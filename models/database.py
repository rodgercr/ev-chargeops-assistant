from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

Base = declarative_base()

class Perfil(Base):
    __tablename__ = "perfis"
    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome     = Column(String(50), unique=True, nullable=False)  # sindico, morador, admin
    descricao = Column(String(200))
    usuarios  = relationship("Usuario", back_populates="perfil")
    prompts   = relationship("SystemPrompt", back_populates="perfil")

class Usuario(Base):
    __tablename__ = "usuarios"
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username   = Column(String(100), unique=True, nullable=False)
    senha_hash = Column(String(200), nullable=False)
    nome       = Column(String(200))
    email      = Column(String(200))
    ativo      = Column(Boolean, default=True)
    perfil_id  = Column(UUID(as_uuid=True), ForeignKey("perfis.id"))
    criado_em  = Column(DateTime, default=datetime.utcnow)
    perfil     = relationship("Perfil", back_populates="usuarios")
    historico  = relationship("HistoricoConversa", back_populates="usuario")

class SystemPrompt(Base):
    __tablename__ = "system_prompts"
    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    perfil_id = Column(UUID(as_uuid=True), ForeignKey("perfis.id"))
    conteudo  = Column(Text, nullable=False)
    versao    = Column(Integer, default=1)
    ativo     = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    perfil    = relationship("Perfil", back_populates="prompts")

class HistoricoConversa(Base):
    __tablename__ = "historico_conversas"
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id  = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    pergunta    = Column(Text, nullable=False)
    resposta    = Column(Text, nullable=False)
    fontes      = Column(Text)
    criado_em   = Column(DateTime, default=datetime.utcnow)
    usuario     = relationship("Usuario", back_populates="historico")
