"""Regras determinísticas executadas antes do modelo de linguagem."""

from __future__ import annotations

from dataclasses import dataclass

from services.guardrails.scope_validator import esta_no_escopo, normalizar_texto


@dataclass(frozen=True)
class ResultadoGuardrail:
    permitido: bool
    categoria: str
    mensagem: str | None = None


PADROES_DE_INJECAO = (
    "bypass",
    "developer message",
    "desconsidere as instrucoes",
    "esqueca as regras",
    "finja que voce nao e",
    "ignore as instrucoes",
    "ignore todas as instrucoes",
    "jailbreak",
    "modo dan",
    "modo desenvolvedor",
    "mostre o prompt do sistema",
    "revele o prompt",
    "sem restricoes",
    "substitua suas instrucoes",
    "system prompt",
)

PADROES_ELETRICOS_PERIGOSOS = (
    "220 v sozinho",
    "220v sozinho",
    "abrir o carregador",
    "burlar o disjuntor",
    "choque eletrico",
    "consertar o carregador",
    "desmontar o carregador",
    "instalar sozinho",
    "ligar os fios",
    "mexer sozinho",
    "reparar o carregador",
    "trocar o disjuntor",
)

PADROES_JURIDICOS = (
    "aconselhamento juridico",
    "devo processar",
    "direito de indenizacao",
    "entrar com uma acao",
    "garantia legal",
    "parecer juridico",
    "posso processar",
)

PADROES_FINANCEIROS = (
    "aconselhamento financeiro",
    "devo investir",
    "garantia de lucro",
    "investimento sem risco",
    "qual acao comprar",
    "retorno garantido",
)

PADROES_ESPECIFICACAO = (
    "ficha tecnica do modelo inexistente",
    "garantia exata do modelo",
    "modelo goodwe xyz-999",
    "preco oficial do modelo inexistente",
)

MENSAGENS = {
    "prompt_injection": (
        "Não posso revelar ou substituir minhas instruções internas. "
        "Posso ajudar com mobilidade elétrica e soluções GoodWe."
    ),
    "seguranca_eletrica": (
        "Por segurança, não forneço instruções para intervenção elétrica. "
        "Desligue o equipamento e procure um eletricista ou instalador habilitado."
    ),
    "juridico": (
        "Não forneço aconselhamento jurídico. Consulte um profissional habilitado "
        "para avaliar o seu caso."
    ),
    "financeiro": (
        "Não forneço aconselhamento financeiro ou promessa de retorno. "
        "Consulte um profissional habilitado."
    ),
    "especificacao_nao_verificada": (
        "Não tenho essa especificação GoodWe confirmada na base e não vou inventá-la. "
        "Consulte a ficha técnica oficial ou o suporte GoodWe."
    ),
    "fora_do_escopo": (
        "Posso ajudar apenas com mobilidade elétrica, recarga, eletropostos e "
        "soluções GoodWe."
    ),
}


def _contem(texto: str, padroes: tuple[str, ...]) -> bool:
    return any(padrao in texto for padrao in padroes)


def contem_tentativa_de_injecao(texto: str) -> bool:
    return _contem(normalizar_texto(texto), PADROES_DE_INJECAO)


def avaliar_guardrails(
    texto: str, *, possui_contexto: bool = False
) -> ResultadoGuardrail:
    """Classifica a entrada antes de qualquer consulta ao RAG ou ao LLM."""
    normalizado = normalizar_texto(texto)
    verificacoes = (
        ("prompt_injection", PADROES_DE_INJECAO),
        ("seguranca_eletrica", PADROES_ELETRICOS_PERIGOSOS),
        ("juridico", PADROES_JURIDICOS),
        ("financeiro", PADROES_FINANCEIROS),
        ("especificacao_nao_verificada", PADROES_ESPECIFICACAO),
    )
    for categoria, padroes in verificacoes:
        if _contem(normalizado, padroes):
            return ResultadoGuardrail(False, categoria, MENSAGENS[categoria])

    if not esta_no_escopo(texto, possui_contexto=possui_contexto):
        return ResultadoGuardrail(False, "fora_do_escopo", MENSAGENS["fora_do_escopo"])

    return ResultadoGuardrail(True, "permitido")
