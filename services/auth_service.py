from datetime import datetime, timedelta
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from models.database import Usuario, SystemPrompt
from models.database import Perfil
from models.connection import get_db
from dotenv import load_dotenv
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
import bcrypt
import os
import re

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM  = os.getenv("ALGORITHM")
EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode()[:72], bcrypt.gensalt()).decode()

def verificar_senha(senha: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(senha.encode()[:72], senha_hash.encode())


def validar_dados_cadastro(
    nome: str,
    username: str,
    email: str,
    password: str,
    confirmar_password: str,
) -> list[str]:
    """Valida o cadastro público sem acessar o banco."""
    erros = []
    if len(nome.strip()) < 2:
        erros.append("Informe seu nome.")
    if not re.fullmatch(r"[a-zA-Z0-9._-]{3,50}", username.strip()):
        erros.append(
            "O usuário deve ter de 3 a 50 caracteres: letras, números, ponto, hífen ou sublinhado."
        )
    if email.strip() and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()):
        erros.append("Informe um e-mail válido ou deixe o campo vazio.")
    if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        erros.append("A senha deve ter pelo menos 8 caracteres, com uma letra e um número.")
    if password != confirmar_password:
        erros.append("As senhas não coincidem.")
    return erros


def criar_conta_morador(
    db: Session,
    *,
    nome: str,
    username: str,
    email: str,
    password: str,
) -> Usuario:
    """Cria uma conta pública sempre com o perfil de menor privilégio: morador."""
    username_normalizado = username.strip().casefold()
    email_normalizado = email.strip().casefold() or None

    existente = db.query(Usuario).filter(
        func.lower(Usuario.username) == username_normalizado
    ).first()
    if existente:
        raise ValueError("Este nome de usuário já está em uso.")

    if email_normalizado:
        email_existente = db.query(Usuario).filter(
            func.lower(Usuario.email) == email_normalizado
        ).first()
        if email_existente:
            raise ValueError("Este e-mail já está cadastrado.")

    perfil = db.query(Perfil).filter(Perfil.nome == "morador").first()
    if perfil is None:
        raise RuntimeError("O perfil de morador ainda não foi configurado no banco.")

    usuario = Usuario(
        username=username_normalizado,
        senha_hash=hash_senha(password),
        nome=nome.strip(),
        email=email_normalizado,
        ativo=True,
        perfil=perfil,
    )
    db.add(usuario)
    try:
        db.commit()
        db.refresh(usuario)
    except IntegrityError as erro:
        db.rollback()
        raise ValueError("Não foi possível usar esse usuário ou e-mail.") from erro
    return usuario

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
