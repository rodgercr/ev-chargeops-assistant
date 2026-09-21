"""Núcleo conversacional LCEL com memória isolada por sessão."""

from __future__ import annotations

import logging
import os
import re
from threading import Lock
from typing import Any

from dotenv import load_dotenv
from langchain_classic.memory import ConversationTokenBufferMemory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_ollama import ChatOllama

from models.consulta_recarga import ConsultaRecarga
from services.guardrails import avaliar_guardrails


load_dotenv()
logger = logging.getLogger(__name__)

MEMORY_MAX_TOKENS = int(os.getenv("MEMORY_MAX_TOKENS", "2000"))


def _token_ids_aproximados(texto: str) -> list[int]:
    """Tokenizador local determinístico usado somente para limitar a memória."""
    partes = re.findall(r"\w+|[^\w\s]", texto, flags=re.UNICODE)
    return list(range(len(partes)))


llm = ChatOllama(
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
    temperature=0.3,
    num_predict=int(os.getenv("OLLAMA_MAX_TOKENS", "512")),
    custom_get_token_ids=_token_ids_aproximados,
)


COLLECTIONS = {
    "sindico": "sindico",
    "admin": "sindico",
    "morador": "atendimento",
}


PROMPT_SINDICO = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """{system_prompt}

<regras_de_resposta>
- Responda sempre em português do Brasil.
- Utilize somente os dados e documentos presentes no contexto.
- Não invente números, ocorrências, usuários ou estados de eletropostos.
- Se o contexto não contiver a resposta, informe claramente essa limitação.
- Considere o histórico da sessão para entender referências como "e o anterior?".
</regras_de_resposta>

<dados_do_banco>
{dados_banco}
</dados_do_banco>

<documentos_rag>
{contexto_docs}
</documentos_rag>""",
        ),
        MessagesPlaceholder(variable_name="historico"),
        ("human", "{pergunta}"),
    ]
)


PROMPT_MORADOR = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """{system_prompt}

<regras_de_resposta>
- Responda sempre em português do Brasil, com linguagem clara e acessível.
- Utilize somente as informações presentes no contexto.
- Nunca exponha dados de outros moradores.
- Não invente tarifas, regras, prazos ou estados de eletropostos.
- Se faltar informação, oriente o usuário a procurar o síndico ou o suporte GoodWe.
- Considere o histórico da sessão para entender referências a mensagens anteriores.
</regras_de_resposta>

<contexto_autorizado>
{contexto}
</contexto_autorizado>""",
        ),
        MessagesPlaceholder(variable_name="historico"),
        ("human", "{pergunta}"),
    ]
)


_memorias: dict[str, ConversationTokenBufferMemory] = {}
_memorias_lock = Lock()


def _obter_memoria(session_id: str) -> ConversationTokenBufferMemory:
    """Cria ou recupera o buffer limitado de uma sessão específica."""
    with _memorias_lock:
        if session_id not in _memorias:
            _memorias[session_id] = ConversationTokenBufferMemory(
                llm=llm,
                memory_key="historico",
                input_key="pergunta",
                output_key="resposta",
                return_messages=True,
                max_token_limit=MEMORY_MAX_TOKENS,
            )
        return _memorias[session_id]


def obter_historico_sessao(session_id: str) -> BaseChatMessageHistory:
    """Função exigida pelo RunnableWithMessageHistory."""
    return _obter_memoria(session_id).chat_memory


def _podar_memoria(session_id: str) -> None:
    """Remove mensagens antigas quando o limite de tokens é ultrapassado."""
    memoria = _obter_memoria(session_id)
    mensagens = memoria.chat_memory.messages
    while mensagens and llm.get_num_tokens_from_messages(mensagens) > MEMORY_MAX_TOKENS:
        mensagens.pop(0)


def _carregar_historico_inicial(
    session_id: str, historico: list[tuple[str, str]]
) -> None:
    """Restaura do banco uma sessão ainda ausente na memória do processo."""
    chat_history = obter_historico_sessao(session_id)
    if chat_history.messages or not historico:
        return

    mensagens = []
    for pergunta, resposta in historico:
        mensagens.extend([HumanMessage(content=pergunta), AIMessage(content=resposta)])
    chat_history.add_messages(mensagens)
    _podar_memoria(session_id)


def criar_chain(perfil: str) -> Runnable:
    """Monta a chain LCEL base adequada ao perfil autenticado."""
    prompt = PROMPT_SINDICO if perfil in {"sindico", "admin"} else PROMPT_MORADOR
    return prompt | llm | StrOutputParser()


def criar_chain_com_memoria(perfil: str) -> RunnableWithMessageHistory:
    """Adiciona memória por session_id à chain LCEL."""
    return RunnableWithMessageHistory(
        criar_chain(perfil),
        obter_historico_sessao,
        input_messages_key="pergunta",
        history_messages_key="historico",
    )


def criar_chain_estruturada() -> Runnable:
    """Extrai os dados da consulta como um objeto Pydantic validado."""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """Extraia apenas os dados explicitamente informados na consulta.
Não invente veículo, potência ou conector. Use null quando um dado não aparecer.
Em potencia_kw, extraia números associados a kW e converta vírgula decimal para ponto:
"7,4 kW" deve resultar em potencia_kw igual a 7.4.
Classifique o local como residencial, comercial, publico ou desconhecido.
Resuma o objetivo principal no campo duvida.
Exemplo: "BYD Dolphin, carregador residencial de 7,4 kW" significa
veiculo="BYD Dolphin", potencia_kw=7.4 e local="residencial".""",
            ),
            ("human", "{consulta}"),
        ]
    )
    llm_estruturado = ChatOllama(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
        temperature=0.0,
        top_p=0.9,
        num_predict=int(os.getenv("OLLAMA_MAX_TOKENS", "512")),
        reasoning=False,
    ).with_structured_output(ConsultaRecarga, method="json_schema")
    return prompt | llm_estruturado


def limpar_memoria_sessao(session_id: str) -> None:
    """Remove apenas a memória da sessão informada."""
    with _memorias_lock:
        memoria = _memorias.pop(session_id, None)
    if memoria:
        memoria.clear()


def estatisticas_memoria(session_id: str) -> dict[str, int]:
    """Retorna métricas sem expor o conteúdo das mensagens."""
    mensagens = obter_historico_sessao(session_id).messages
    return {
        "mensagens": len(mensagens),
        "tokens": llm.get_num_tokens_from_messages(mensagens),
        "limite_tokens": MEMORY_MAX_TOKENS,
    }


def _executar_chain(perfil: str, session_id: str, dados: dict[str, Any]) -> str:
    chain = criar_chain_com_memoria(perfil)
    resposta = chain.invoke(
        dados,
        config={"configurable": {"session_id": session_id}},
    )
    _podar_memoria(session_id)
    return resposta


def gerar_resposta(
    pergunta: str,
    system_prompt: str,
    perfil: str,
    db=None,
    usuario_id: str | None = None,
    session_id: str | None = None,
    historico: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Gera resposta com RAG, dados relacionais e memória por sessão."""
    session_id = session_id or f"legado:{perfil}:{usuario_id or 'anonimo'}"
    _carregar_historico_inicial(session_id, historico or [])

    decisao_guardrail = avaliar_guardrails(
        pergunta,
        possui_contexto=bool(obter_historico_sessao(session_id).messages),
    )
    if not decisao_guardrail.permitido:
        logger.info(
            "Entrada bloqueada pelo guardrail %s na sessão %s",
            decisao_guardrail.categoria,
            session_id,
        )
        return {
            "resposta": decisao_guardrail.mensagem,
            "fontes": [],
            "session_id": session_id,
            "guardrail": decisao_guardrail.categoria,
        }

    # O serviço de embeddings é carregado somente quando uma consulta realmente usa RAG.
    # Assim, testes de guardrails e da chain não iniciam o modelo de embeddings.
    from services.rag_service import buscar_contexto

    if perfil in {"sindico", "admin"} and db is not None:
        from services.db_context_service import contexto_sindico

        dados_banco = contexto_sindico(db, pergunta)
        contexto_docs, fontes = buscar_contexto(COLLECTIONS[perfil], pergunta)
        entradas = {
            "system_prompt": system_prompt,
            "dados_banco": dados_banco or "Nenhum dado relacional encontrado.",
            "contexto_docs": contexto_docs or "Nenhum documento adicional encontrado.",
            "pergunta": pergunta,
        }
    else:
        dados_banco = ""
        if db is not None and usuario_id:
            from services.db_context_service import contexto_morador

            dados_banco = contexto_morador(db, pergunta, usuario_id)

        contexto_docs, fontes = buscar_contexto(
            COLLECTIONS.get(perfil, "atendimento"), pergunta
        )
        contexto_autorizado = "\n\n".join(
            parte for parte in (dados_banco, contexto_docs) if parte
        )
        entradas = {
            "system_prompt": system_prompt,
            "contexto": contexto_autorizado or "Nenhuma informação adicional disponível.",
            "pergunta": pergunta,
        }

    try:
        resposta = _executar_chain(perfil, session_id, entradas)
        return {"resposta": resposta, "fontes": fontes, "session_id": session_id}
    except Exception:
        logger.exception(
            "Falha ao executar a chain LCEL do perfil %s na sessão %s",
            perfil,
            session_id,
        )
        return {
            "resposta": (
                "Desculpe, não consegui processar a solicitação agora. "
                "Verifique se o Ollama está ativo e tente novamente."
            ),
            "fontes": [],
            "session_id": session_id,
        }
