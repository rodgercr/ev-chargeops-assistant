from pydantic import BaseModel, Field, field_validator
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
    session_id: Optional[str] = Field(default=None, max_length=100)

    @field_validator("session_id")
    @classmethod
    def normalizar_session_id(cls, valor: Optional[str]) -> Optional[str]:
        if valor is None:
            return None
        valor = valor.strip()
        return valor or None

class ChatResponse(BaseModel):
    resposta: str
    fontes: list[str] = Field(default_factory=list)
    session_id: str

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
    session_id: Optional[str]
    pergunta: str
    resposta: str
    fontes: Optional[str]
    criado_em: datetime
