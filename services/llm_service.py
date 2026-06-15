from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from services.rag_service import buscar_contexto
from dotenv import load_dotenv
import os

load_dotenv()

llm = OllamaLLM(
    base_url=os.getenv("OLLAMA_BASE_URL"),
    model=os.getenv("OLLAMA_MODEL"),
    temperature=0.3
)

COLLECTIONS = {
    "sindico": "sindico",
    "admin":   "sindico",
    "morador": "atendimento",
}

TEMPLATE_SINDICO = PromptTemplate(
    input_variables=["system_prompt", "historico", "dados_banco", "contexto_docs", "pergunta"],
    template="""{system_prompt}

HISTÓRICO DA CONVERSA (mensagens anteriores, use para entender o contexto de perguntas curtas como "e o anterior?"):
---
{historico}
---

DADOS REAIS DO BANCO DE DADOS (use estes para responder com precisão):
---
{dados_banco}
---

DOCUMENTOS DE APOIO:
---
{contexto_docs}
---

Pergunta do síndico: {pergunta}

Responda de forma direta e objetiva usando os dados acima. Cite valores exatos quando disponíveis. Leve em conta o histórico da conversa para entender referências a mensagens anteriores.
Resposta:"""
)

TEMPLATE_MORADOR = PromptTemplate(
    input_variables=["system_prompt", "historico", "contexto", "pergunta"],
    template="""{system_prompt}

HISTÓRICO DA CONVERSA (mensagens anteriores, use para entender o contexto):
---
{historico}
---

Informações disponíveis:
---
{contexto}
---

Pergunta: {pergunta}

Leve em conta o histórico da conversa para entender referências a mensagens anteriores.
Resposta:"""
)


def _formatar_historico(historico: list) -> str:
    """Recebe lista de tuplas (pergunta, resposta) e formata para o prompt."""
    if not historico:
        return "Nenhuma mensagem anterior. Esta é a primeira pergunta da conversa."
    linhas = []
    for pergunta, resposta in historico:
        linhas.append(f"Usuário: {pergunta}")
        linhas.append(f"Assistente: {resposta}")
    return "\n".join(linhas)


def gerar_resposta(pergunta: str, system_prompt: str, perfil: str, db=None, usuario_id: str = None, historico: list = None) -> dict:
    historico_txt = _formatar_historico(historico or [])

    # ── AGENTE SÍNDICO / ADMIN: acesso total ao banco ──
    if perfil in ["sindico", "admin"] and db is not None:
        from services.db_context_service import contexto_sindico
        dados_banco = contexto_sindico(db, pergunta)
        contexto_docs, fontes = buscar_contexto(COLLECTIONS[perfil], pergunta)
        prompt = TEMPLATE_SINDICO.format(
            system_prompt=system_prompt,
            historico=historico_txt,
            dados_banco=dados_banco,
            contexto_docs=contexto_docs or "Nenhum documento adicional.",
            pergunta=pergunta
        )
        try:
            resposta = llm.invoke(prompt)
            return {"resposta": resposta, "fontes": fontes}
        except:
            return {"resposta": "Erro ao processar. Tente novamente.", "fontes": []}

    # ── AGENTE MORADOR: acesso restrito aos próprios dados ──
    dados_banco = ""
    if db is not None and usuario_id:
        from services.db_context_service import contexto_morador
        dados_banco = contexto_morador(db, pergunta, usuario_id)

    contexto_docs, fontes = buscar_contexto(COLLECTIONS.get(perfil, "atendimento"), pergunta)
    todos_contextos = "\n\n".join(filter(None, [dados_banco, contexto_docs])) or "Nenhuma informação adicional disponível."

    prompt = TEMPLATE_MORADOR.format(
        system_prompt=system_prompt,
        historico=historico_txt,
        contexto=todos_contextos,
        pergunta=pergunta
    )
    try:
        resposta = llm.invoke(prompt)
        return {"resposta": resposta, "fontes": fontes}
    except:
        return {
            "resposta": "Desculpe, estou com dificuldades técnicas. Tente novamente em instantes.",
            "fontes": []
        }
