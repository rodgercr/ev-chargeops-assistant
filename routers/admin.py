from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.schemas import UsuarioCreate, UsuarioResponse, PromptUpdate, PromptResponse, HistoricoResponse
from models.database import Usuario, Perfil, SystemPrompt, HistoricoConversa
from models.connection import get_db
from routers.auth import get_usuario_atual
from services.auth_service import hash_senha
from uuid import UUID

router = APIRouter()

def exige_admin(usuario=Depends(get_usuario_atual)):
    if usuario.perfil.nome != "admin":
        raise HTTPException(status_code=403, detail="Somente administradores")
    return usuario

# ── USUÁRIOS ──
@router.get("/usuarios", response_model=list[UsuarioResponse])
def listar_usuarios(db: Session = Depends(get_db), _=Depends(exige_admin)):
    usuarios = db.query(Usuario).all()
    return [UsuarioResponse(
        id=u.id, username=u.username, nome=u.nome or "",
        email=u.email, ativo=u.ativo,
        perfil=u.perfil.nome if u.perfil else "",
        criado_em=u.criado_em
    ) for u in usuarios]

@router.post("/usuarios", response_model=UsuarioResponse)
def criar_usuario(dados: UsuarioCreate, db: Session = Depends(get_db), _=Depends(exige_admin)):
    perfil = db.query(Perfil).filter(Perfil.nome == dados.perfil_nome).first()
    if not perfil:
        raise HTTPException(status_code=404, detail=f"Perfil '{dados.perfil_nome}' não encontrado")
    if db.query(Usuario).filter(Usuario.username == dados.username).first():
        raise HTTPException(status_code=400, detail="Username já existe")
    usuario = Usuario(
        username=dados.username,
        senha_hash=hash_senha(dados.password),
        nome=dados.nome,
        email=dados.email,
        perfil_id=perfil.id
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return UsuarioResponse(
        id=usuario.id, username=usuario.username,
        nome=usuario.nome or "", email=usuario.email,
        ativo=usuario.ativo, perfil=perfil.nome,
        criado_em=usuario.criado_em
    )

@router.patch("/usuarios/{uid}/ativo")
def toggle_usuario(uid: UUID, ativo: bool, db: Session = Depends(get_db), _=Depends(exige_admin)):
    u = db.query(Usuario).filter(Usuario.id == str(uid)).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    u.ativo = ativo
    db.commit()
    return {"ok": True}

# ── SYSTEM PROMPTS ──
@router.get("/prompts", response_model=list[PromptResponse])
def listar_prompts(db: Session = Depends(get_db), _=Depends(exige_admin)):
    prompts = db.query(SystemPrompt).filter(SystemPrompt.ativo == True).all()
    return [PromptResponse(
        id=p.id, perfil=p.perfil.nome if p.perfil else "",
        conteudo=p.conteudo, versao=p.versao,
        ativo=p.ativo, criado_em=p.criado_em
    ) for p in prompts]

@router.put("/prompts/{perfil_nome}")
def atualizar_prompt(perfil_nome: str, dados: PromptUpdate, db: Session = Depends(get_db), _=Depends(exige_admin)):
    perfil = db.query(Perfil).filter(Perfil.nome == perfil_nome).first()
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    # desativa o prompt atual
    db.query(SystemPrompt).filter(
        SystemPrompt.perfil_id == perfil.id,
        SystemPrompt.ativo == True
    ).update({"ativo": False})
    # calcula próxima versão
    ultima = db.query(SystemPrompt).filter(SystemPrompt.perfil_id == perfil.id).count()
    novo = SystemPrompt(
        perfil_id=perfil.id,
        conteudo=dados.conteudo,
        versao=ultima + 1,
        ativo=True
    )
    db.add(novo)
    db.commit()
    return {"ok": True, "versao": novo.versao}

# ── HISTÓRICO ──
@router.get("/historico", response_model=list[HistoricoResponse])
def listar_historico(limite: int = 50, db: Session = Depends(get_db), _=Depends(exige_admin)):
    registros = db.query(HistoricoConversa).order_by(
        HistoricoConversa.criado_em.desc()
    ).limit(limite).all()
    return [HistoricoResponse(
        id=r.id,
        usuario=r.usuario.username if r.usuario else "—",
        session_id=r.session_id,
        pergunta=r.pergunta,
        resposta=r.resposta,
        fontes=r.fontes,
        criado_em=r.criado_em
    ) for r in registros]
