"""Validação de escopo para mobilidade elétrica e EV ChargeOps."""

from __future__ import annotations

import re
import unicodedata


TERMOS_DO_ESCOPO = {
    "apartamento",
    "autonomia",
    "bateria",
    "carregador",
    "carregamento",
    "carro eletrico",
    "condominio",
    "conector",
    "consumo",
    "credito de energia",
    "disjuntor",
    "eletroposto",
    "energia",
    "ev",
    "fatura",
    "goodwe",
    "incidente",
    "instalacao",
    "kwh",
    "morador",
    "pagamento",
    "potencia",
    "recarga",
    "reserva",
    "sessao de carga",
    "sessoes de carga",
    "sindico",
    "solar",
    "suporte",
    "tarifa",
    "veiculo eletrico",
    "wallbox",
}

SAUDACOES = {
    "ajuda",
    "boa noite",
    "boa tarde",
    "bom dia",
    "menu",
    "ola",
    "oi",
}

PADROES_DE_CONTINUACAO = (
    r"^(e\s+)?(o|a|os|as)?\s*(anterior|ultimo|ultima|primeiro|primeira)\b",
    r"^(e\s+)?(isso|esse|essa|ele|ela|eles|elas)\b",
    r"^(e\s+)?(qual|quais|quanto|quantos|como|quando|onde|por que)\b",
    r"^(pode|consegue)\s+(explicar|detalhar|repetir|resumir)\b",
    r"^(me\s+)?(explique|detalhe|resuma|repita)\b",
)


def normalizar_texto(texto: str) -> str:
    """Remove acentos e diferenças de caixa sem alterar o texto original."""
    sem_acentos = "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", texto.casefold())
        if unicodedata.category(caractere) != "Mn"
    )
    return " ".join(sem_acentos.split())


def parece_continuacao(texto: str) -> bool:
    """Reconhece referências curtas a uma mensagem anterior."""
    normalizado = normalizar_texto(texto).strip(" ?.!")
    if len(normalizado.split()) > 12:
        return False
    return any(re.search(padrao, normalizado) for padrao in PADROES_DE_CONTINUACAO)


def esta_no_escopo(texto: str, possui_contexto: bool = False) -> bool:
    """Aceita temas EV, saudações e continuações válidas de uma sessão."""
    texto_normalizado = normalizar_texto(texto)
    if texto_normalizado.strip(" ?.!") in SAUDACOES:
        return True
    if any(
        re.search(rf"(?<!\w){re.escape(termo)}s?(?!\w)", texto_normalizado)
        for termo in TERMOS_DO_ESCOPO
    ):
        return True
    return possui_contexto and parece_continuacao(texto)
