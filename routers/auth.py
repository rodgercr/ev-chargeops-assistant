from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from models.schemas import UserLogin, Token
from models.connection import get_db
from services.auth_service import autenticar_usuario, criar_token, verificar_token
from models.database import Usuario

router   = APIRouter()
security = HTTPBearer()

@router.post("/login", response_model=Token)
def login(dados: UserLogin, db: Session = Depends(get_db)):
    usuario = autenticar_usuario(db, dados.username, dados.password)
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuário ou senha incorretos")
    token = criar_token({
        "sub": str(usuario.id),
        "username": usuario.username,
        "perfil": usuario.perfil.nome
    })
    return Token(
        access_token=token,
        token_type="bearer",
        perfil=usuario.perfil.nome,
        nome=usuario.nome or usuario.username
    )

def get_usuario_atual(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    payload = verificar_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    usuario = db.query(Usuario).filter(Usuario.id == payload["sub"]).first()
    if not usuario or not usuario.ativo:
        raise HTTPException(status_code=401, detail="Usuário inativo ou não encontrado")
    return usuario
