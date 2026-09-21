"""Executa a suíte reproduzível de avaliações da Sprint 3."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from services.guardrails import avaliar_guardrails


def contar_tokens(texto: str) -> int:
    """Conta tokens com tiktoken e usa aproximação local como fallback."""
    try:
        import tiktoken

        return len(tiktoken.get_encoding("cl100k_base").encode(texto))
    except (ImportError, ModuleNotFoundError):
        return len(re.findall(r"\w+|[^\w\s]", texto, flags=re.UNICODE))


def nome_seguro_modelo(modelo: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", modelo).strip("_").casefold()


def contem_termos(texto: str, termos: list[str]) -> bool:
    normalizado = texto.casefold().replace(",", ".")
    return all(termo.casefold().replace(",", ".") in normalizado for termo in termos)


def executar_guardrail(teste: dict[str, Any]) -> dict[str, Any]:
    inicio = time.perf_counter()
    decisao = avaliar_guardrails(teste["pergunta"])
    resposta = decisao.mensagem or "permitido"
    return {
        "id": teste["id"],
        "categoria": teste["categoria"],
        "aprovado": (
            not decisao.permitido and decisao.categoria == teste["categoria"]
        ),
        "latencia_segundos": round(time.perf_counter() - inicio, 4),
        "tokens_entrada": contar_tokens(teste["pergunta"]),
        "tokens_saida": contar_tokens(resposta),
        "resposta": resposta,
        "categoria_detectada": decisao.categoria,
    }


def entradas_chat(pergunta: str) -> dict[str, str]:
    return {
        "system_prompt": (
            "Você é o GoodWe AI, assistente de mobilidade elétrica. "
            "Responda somente com base no contexto fornecido."
        ),
        "contexto": (
            "A recarga residencial utiliza um carregador compatível com o veículo. "
            "O tempo varia conforme a capacidade da bateria e a potência disponível."
        ),
        "pergunta": pergunta,
    }


def executar_com_modelo(
    teste: dict[str, Any], chain: Any, chain_estruturada: Any
) -> dict[str, Any]:
    from services.llm_service import limpar_memoria_sessao

    inicio = time.perf_counter()
    tipo = teste["tipo"]

    if tipo == "structured":
        dados = chain_estruturada.invoke({"consulta": teste["pergunta"]})
        obtidos = dados.model_dump()
        esperado = teste["campos_esperados"]
        aprovado = all(obtidos.get(campo) == valor for campo, valor in esperado.items())
        resposta = dados.model_dump_json()
        detalhes = {"campos_obtidos": obtidos}
        entrada = teste["pergunta"]
    elif tipo == "memoria":
        sessao = f"eval-{uuid.uuid4()}"
        respostas = []
        for mensagem in teste["mensagens"]:
            respostas.append(
                chain.invoke(
                    entradas_chat(mensagem),
                    config={"configurable": {"session_id": sessao}},
                )
            )
        resposta = respostas[-1]
        aprovado = contem_termos(resposta, teste["termos_esperados"])
        detalhes = {"turnos": len(teste["mensagens"])}
        entrada = "\n".join(teste["mensagens"])
        limpar_memoria_sessao(sessao)
    else:
        sessao = f"eval-{uuid.uuid4()}"
        resposta = chain.invoke(
            entradas_chat(teste["pergunta"]),
            config={"configurable": {"session_id": sessao}},
        )
        aprovado = contem_termos(resposta, teste["termos_esperados"])
        detalhes = {}
        entrada = teste["pergunta"]
        limpar_memoria_sessao(sessao)

    return {
        "id": teste["id"],
        "categoria": teste["categoria"],
        "aprovado": aprovado,
        "latencia_segundos": round(time.perf_counter() - inicio, 3),
        "tokens_entrada": contar_tokens(entrada),
        "tokens_saida": contar_tokens(resposta),
        "resposta": resposta,
        **detalhes,
    }


def salvar_relatorio(
    resultados: list[dict[str, Any]], modelo: str, somente_guardrails: bool
) -> Path:
    aprovados = sum(bool(resultado.get("aprovado")) for resultado in resultados)
    latencias = [
        resultado["latencia_segundos"]
        for resultado in resultados
        if "latencia_segundos" in resultado
    ]
    relatorio = {
        "executado_em": datetime.now(timezone.utc).isoformat(),
        "modelo": "nao_aplicavel" if somente_guardrails else modelo,
        "modo": "somente_guardrails" if somente_guardrails else "completo",
        "parametros": {
            "temperature": 0.3,
            "max_tokens_saida": int(os.getenv("OLLAMA_MAX_TOKENS", "256")),
            "max_tokens_memoria": int(os.getenv("MEMORY_MAX_TOKENS", "2000")),
        },
        "total_testes": len(resultados),
        "aprovados": aprovados,
        "taxa_sucesso_percentual": round(aprovados / len(resultados) * 100, 2),
        "latencia_media_segundos": (
            round(sum(latencias) / len(latencias), 3) if latencias else 0
        ),
        "resultados": resultados,
    }
    destino = RAIZ / "evals" / (
        "sprint3_results_guardrails.json"
        if somente_guardrails
        else f"sprint3_results_{nome_seguro_modelo(modelo)}.json"
    )
    conteudo = json.dumps(relatorio, ensure_ascii=False, indent=2)
    destino.write_text(conteudo, encoding="utf-8")
    if not somente_guardrails:
        (RAIZ / "evals" / "sprint3_results.json").write_text(
            conteudo, encoding="utf-8"
        )
    return destino


def main() -> None:
    load_dotenv(RAIZ / ".env")
    parser = argparse.ArgumentParser(description="Executa os evals da Sprint 3.")
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "llama3.2:3b"))
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument(
        "--somente-guardrails",
        action="store_true",
        help="Executa os casos determinísticos sem iniciar o Ollama.",
    )
    argumentos = parser.parse_args()

    os.environ["OLLAMA_MODEL"] = argumentos.model
    os.environ["OLLAMA_MAX_TOKENS"] = str(argumentos.max_tokens)
    testes = json.loads(
        (RAIZ / "evals" / "eval_set.json").read_text(encoding="utf-8")
    )
    if argumentos.somente_guardrails:
        testes = [teste for teste in testes if teste["tipo"] == "guardrail"]
        chain = chain_estruturada = None
    else:
        from services.llm_service import criar_chain_com_memoria, criar_chain_estruturada

        chain = criar_chain_com_memoria("morador")
        chain_estruturada = criar_chain_estruturada()

    resultados = []
    for teste in testes:
        try:
            if teste["tipo"] == "guardrail":
                resultado = executar_guardrail(teste)
            else:
                resultado = executar_com_modelo(teste, chain, chain_estruturada)
        except Exception as erro:
            resultado = {
                "id": teste["id"],
                "categoria": teste["categoria"],
                "aprovado": False,
                "erro": f"{type(erro).__name__}: {erro}",
            }
        resultados.append(resultado)
        status = "PASSOU" if resultado["aprovado"] else "FALHOU"
        print(f"[{status}] {teste['id']} - {teste['categoria']}")

    destino = salvar_relatorio(
        resultados, argumentos.model, argumentos.somente_guardrails
    )
    aprovados = sum(bool(resultado.get("aprovado")) for resultado in resultados)
    print(f"\nResultado: {aprovados}/{len(resultados)}")
    print(f"Relatório salvo em: {destino}")


if __name__ == "__main__":
    main()
