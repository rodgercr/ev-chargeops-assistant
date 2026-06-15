from datetime import datetime, timedelta
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from models.database import Usuario, SystemPrompt
from models.connection import get_db
from dotenv import load_dotenv
import bcrypt
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM  = os.getenv("ALGORITHM")
EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode()[:72], bcrypt.gensalt()).decode()

def verificar_senha(senha: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(senha.encode()[:72], senha_hash.encode())

def autenticar_usuario(db: Session, username: str, password: str):
    usuario = db.query(Usuario).filter(
        Usuario.username == username,
        Usuario.ativo == True
    ).first()
    if not usuario or not verificar_senha(password, usuario.senha_hash):
        return None
    return usuario

def criar_token(data: dict) -> str:
    dados = data.copy()
    dados["exp"] = datetime.utcnow() + timedelta(minutes=EXPIRE_MIN)
    return jwt.encode(dados, SECRET_KEY, algorithm=ALGORITHM)

def verificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

def get_system_prompt(db: Session, perfil_nome: str) -> str:
    prompt = (
        db.query(SystemPrompt)
        .join(SystemPrompt.perfil)
        .filter(
            SystemPrompt.ativo == True,
            SystemPrompt.perfil.has(nome=perfil_nome)
        )
        .order_by(SystemPrompt.versao.desc())
        .first()
    )
    if prompt:
        return prompt.conteudo
    return "Você é o GoodWe AI, assistente virtual da GoodWeAI. Seja prestativo e objetivo."
