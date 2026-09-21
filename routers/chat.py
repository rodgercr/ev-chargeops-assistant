from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models.schemas import ChatRequest, ChatResponse
from models.database import HistoricoConversa
from models.connection import get_db
from routers.auth import get_usuario_atual
from services.auth_service import get_system_prompt
from services.llm_service import gerar_resposta
import json
import uuid

router = APIRouter()

# Quantas trocas anteriores enviar como memória de contexto
MAX_HISTORICO = 5


def buscar_historico(db: Session, usuario_id, session_id: str) -> list:
    """Busca somente as últimas trocas da sessão informada."""
    registros = db.query(HistoricoConversa).filter(
        HistoricoConversa.usuario_id == usuario_id,
        HistoricoConversa.session_id == session_id,
    ).order_by(desc(HistoricoConversa.criado_em)).limit(MAX_HISTORICO).all()
    # Inverte para ordem cronológica (mais antigo primeiro)
    registros.reverse()
    return [(r.pergunta, r.resposta) for r in registros]


@router.post("/sindico", response_model=ChatResponse)
def chat_sindico(
    request: ChatRequest,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    if usuario.perfil.nome not in ["sindico", "admin"]:
        raise HTTPException(status_code=403, detail="Acesso negado")

    session_id = request.session_id or str(uuid.uuid4())
    system_prompt = get_system_prompt(db, usuario.perfil.nome)
    historico = buscar_historico(db, usuario.id, session_id)

    resultado = gerar_resposta(
        request.pergunta, system_prompt, usuario.perfil.nome,
        db=db, usuario_id=str(usuario.id), session_id=session_id, historico=historico
    )

    db.add(HistoricoConversa(
        usuario_id=usuario.id,
        session_id=session_id,
        pergunta=request.pergunta,
        resposta=resultado["resposta"],
        fontes=json.dumps(resultado["fontes"])
    ))
    db.commit()

    return ChatResponse(
        resposta=resultado["resposta"],
        fontes=resultado["fontes"],
        session_id=session_id,
    )


@router.post("/morador", response_model=ChatResponse)
def chat_morador(
    request: ChatRequest,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_atual)
):
    session_id = request.session_id or str(uuid.uuid4())
    system_prompt = get_system_prompt(db, "morador")
    historico = buscar_historico(db, usuario.id, session_id)

    resultado = gerar_resposta(
        request.pergunta, system_prompt, "morador",
        db=db, usuario_id=str(usuario.id), session_id=session_id, historico=historico
    )

    db.add(HistoricoConversa(
        usuario_id=usuario.id,
        session_id=session_id,
        pergunta=request.pergunta,
        resposta=resultado["resposta"],
        fontes=json.dumps(resultado["fontes"])
    ))
    db.commit()

    return ChatResponse(
        resposta=resultado["resposta"],
        fontes=resultado["fontes"],
        session_id=session_id,
    )
