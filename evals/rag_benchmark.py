"""Utilitários puros do benchmark: validação, agregação pareada e relatório."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from statistics import mean

VARIANTS = ("documentos_inteiros", "trechos_400_80")
METRICS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def load_cases(path: Path, documents: list) -> list[dict]:
    cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
    if not cases:
        raise ValueError("Dataset vazio")
    docs = {doc.doc_id: doc for doc in documents}
    seen = set()
    for case in cases:
        if case["id"] in seen:
            raise ValueError("ID de caso duplicado")
        seen.add(case["id"])
        if case["profile"] not in {"morador", "sindico"}:
            raise ValueError("Perfil inválido")
        if not case["question"].strip() or not case["reference"].strip() or not case["source_ids"]:
            raise ValueError("Pergunta, referência e fontes são obrigatórias")
        collection = "atendimento" if case["profile"] == "morador" else "sindico"
        for source in case["source_ids"]:
            if source not in docs or collection not in docs[source].colecoes:
                raise ValueError("Fonte inexistente ou incompatível com o perfil")
    return cases


def valid_score(value) -> bool:
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def summarize(rows: list[dict], expected: int) -> dict:
    summary = {}
    for variant in VARIANTS:
        group = [row for row in rows if row["variant"] == variant]
        summary[variant] = {}
        for metric in (*METRICS, "source_recall", "retrieval_seconds", "generation_seconds", "context_chars"):
            values = [row.get("scores", {}).get(metric) if metric in METRICS else row.get(metric) for row in group]
            valid = [float(value) for value in values if valid_score(value)]
            summary[variant][metric] = {"mean": mean(valid) if valid else None, "valid": len(valid), "expected": expected}
    paired = {}
    left = {row["id"]: row for row in rows if row["variant"] == VARIANTS[0]}
    right = {row["id"]: row for row in rows if row["variant"] == VARIANTS[1]}
    for metric in METRICS:
        pairs = [(left[key].get("scores", {}).get(metric), right[key].get("scores", {}).get(metric)) for key in left.keys() & right.keys()]
        pairs = [(a, b) for a, b in pairs if valid_score(a) and valid_score(b)]
        paired[metric] = {
            "baseline": mean(a for a, _ in pairs) if pairs else None,
            "candidate": mean(b for _, b in pairs) if pairs else None,
            "delta": mean(b - a for a, b in pairs) if pairs else None,
            "valid_pairs": len(pairs), "expected": expected,
        }
    summary["paired"] = paired
    return summary


def report_markdown(result: dict) -> str:
    summary = summarize(result["rows"], len(result["cases"]))
    def fmt(value):
        return "N/D" if value is None else f"{value:.3f}"
    config = result["config"]
    lines = [
        "# Comparação do RAG — Sprint 4", "",
        f"Execução real iniciada em {result['started_at']} (UTC). Estado: **{result['status']}**.",
        f"Casos previstos: {len(result['cases'])}; respostas registradas: {len(result['rows'])}.",
        "", "## Desenho do experimento", "",
        "- Baseline: documentos inteiros, busca por similaridade cosseno, top-3.",
        "- Candidato: divisão recursiva de até 400 caracteres, sobreposição máxima de 80, top-3.",
        "- Mesma base, embeddings, perguntas, perfis, prompts e modelo nas duas configurações.",
        f"- Gerador: {config['generator']}; juiz: {config['judge']}; temperatura 0; seed 42.",
        f"- Embeddings: {config['embedding']}; relevância com strictness={config['strictness']}.",
        "- Prompts do chatbot e recuperação compartilhada; sem PostgreSQL, memória ou guardrails nesta medição isolada.",
        "- Coleções reconstruídas em data/ragas_chroma, sem alterar os índices usados pelo aplicativo.",
        "- As referências esperadas não são enviadas ao gerador. São utilizadas apenas pelo avaliador.",
        "", "## Métricas RAGAS (comparação pareada)", "",
        "| Métrica | Atual | Candidato | Diferença | Pares válidos |",
        "|---|---:|---:|---:|---:|",
    ]
    for metric, values in summary["paired"].items():
        lines.append(f"| {metric} | {fmt(values['baseline'])} | {fmt(values['candidate'])} | {fmt(values['delta'])} | {values['valid_pairs']}/{values['expected']} |")
    lines += ["", "As médias acima usam somente perguntas com nota válida nas duas versões. Falhas são null, nunca zero.", "", "## Medições auxiliares", "", "| Medida | Atual | Candidato |", "|---|---:|---:|"]
    for metric in ("source_recall", "retrieval_seconds", "generation_seconds", "context_chars"):
        a, b = (summary[v][metric] for v in VARIANTS)
        lines.append(f"| {metric} | {fmt(a['mean'])} ({a['valid']}/{a['expected']}) | {fmt(b['mean'])} ({b['valid']}/{b['expected']}) |")
    lines += [
        "", "source_recall é cobertura de IDs dos documentos esperados (não uma métrica RAGAS).",
        "Latência de geração inclui a chamada local e eventual carregamento do modelo; não inclui avaliação pelo juiz.",
        "Tempos dependem de hardware, aquecimento e ordem de execução; não representam um benchmark rigoroso de velocidade.",
        "", "## Interpretação e limites", "",
        "- Faithfulness: quanto da resposta está sustentado pelos contextos recuperados.",
        "- Answer relevancy: alinhamento entre resposta e pergunta; não mede correção factual.",
        "- Context precision: relevância/ordenação dos contextos em relação à referência.",
        "- Context recall: cobertura das afirmações da referência pelos contextos.",
        "- Valores são avaliações automáticas, não porcentagens de aprovação nem garantia de segurança.",
        "- Juiz local pequeno pode errar; revisar respostas e julgamentos antes da entrega.",
        "- Dataset pequeno, autorado com IA a partir de cinco documentos acadêmicos; não é teste externo nem validação de manuais oficiais GoodWe.",
        "- Casos de dado ausente devem admitir a limitação. Uma recusa correta pode receber baixa relevância; revisar esses casos separadamente.",
        "- Prompts internos do RAGAS permanecem em inglês; a pergunta regenerada para relevância é solicitada em português.",
        "- Uma execução por configuração, sem significância estatística. Seed não garante determinismo entre máquinas.",
        "- O candidato não foi promovido automaticamente para o chatbot. Não presumir que dividir documentos melhora o resultado.",
        "", "## Erros observados", "",
    ]
    errors = [(row["id"], row["variant"], row.get("errors", {})) for row in result["rows"] if row.get("errors")]
    lines.extend(f"- {case} / {variant}: {json.dumps(error, ensure_ascii=False)}" for case, variant, error in errors)
    if not errors:
        lines.append("Nenhum erro registrado até este ponto da execução.")
    lines += ["", "## Evidências e reprodução", "", "O results.json desta pasta contém respostas, contextos ordenados, fontes, distâncias, tokens medidos pelo Ollama, julgamentos, versões, hashes e notas individuais.", "", "Execute executar_ragas.cmd para uma nova comparação. Para retomar: executar_ragas.cmd --resume CAMINHO_DO_RESULTS_JSON.", "", "Referência: [documentação RAGAS](https://docs.ragas.io/en/latest/).", ""]
    return "\n".join(lines)
