from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    perfil: str
    nome: str

class ChatRequest(BaseModel):
    pergunta: str

class ChatResponse(BaseModel):
    resposta: str
    fontes: list[str] = []

class UsuarioCreate(BaseModel):
    username: str
    password: str
    nome: str
    email: Optional[str] = None
    perfil_nome: str

class UsuarioResponse(BaseModel):
    id: UUID
    username: str
    nome: str
    email: Optional[str]
    ativo: bool
    perfil: str
    criado_em: datetime

class PromptUpdate(BaseModel):
    conteudo: str

class PromptResponse(BaseModel):
    id: UUID
    perfil: str
    conteudo: str
    versao: int
    ativo: bool
    criado_em: datetime

class HistoricoResponse(BaseModel):
    id: UUID
    usuario: str
    pergunta: str
    resposta: str
    fontes: Optional[str]
    criado_em: datetime
