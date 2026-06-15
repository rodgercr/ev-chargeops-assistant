from sqlalchemy import Column, String, Boolean, DateTime, Float, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from models.connection import engine
from models.database import Base

class Eletroposto(Base):
    __tablename__ = "eletropostos"
    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo       = Column(String(50), unique=True, nullable=False)  # ex: "EP-01", "EP-02"
    localizacao  = Column(String(200))                              # ex: "Garagem B - Vaga 12"
    potencia_kw  = Column(Float, default=7.4)
    tarifa_kwh   = Column(Float, default=1.20)
    status       = Column(String(50), default="online")            # online, offline, manutencao, falha
    instalado_em = Column(DateTime, default=datetime.utcnow)
    sessoes      = relationship("SessaoCarregamento", back_populates="eletroposto")
    incidentes   = relationship("Incidente", back_populates="eletroposto")

class SessaoCarregamento(Base):
    __tablename__ = "sessoes_carregamento"
    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id      = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    eletroposto_id  = Column(UUID(as_uuid=True), ForeignKey("eletropostos.id"), nullable=False)
    inicio          = Column(DateTime, nullable=False)
    fim             = Column(DateTime)
    duracao_minutos = Column(Integer)
    energia_kwh     = Column(Float)
    tarifa_kwh      = Column(Float, default=0.75)   # R$/kWh
    custo_total     = Column(Float)
    status          = Column(String(50), default="concluida")  # em_andamento, concluida, cancelada, erro
    observacao      = Column(Text)
    criado_em       = Column(DateTime, default=datetime.utcnow)
    usuario         = relationship("Usuario", backref="sessoes")
    eletroposto     = relationship("Eletroposto", back_populates="sessoes")
    fatura          = relationship("Fatura", back_populates="sessao", uselist=False)

class Fatura(Base):
    __tablename__ = "faturas"
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sessao_id  = Column(UUID(as_uuid=True), ForeignKey("sessoes_carregamento.id"), nullable=False)
    valor      = Column(Float, nullable=False)
    status     = Column(String(50), default="pendente")  # pendente, pago, cancelado, inadimplente
    vencimento = Column(DateTime)
    pago_em    = Column(DateTime)
    criado_em  = Column(DateTime, default=datetime.utcnow)
    sessao     = relationship("SessaoCarregamento", back_populates="fatura")

class Incidente(Base):
    __tablename__ = "incidentes"
    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id      = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    eletroposto_id  = Column(UUID(as_uuid=True), ForeignKey("eletropostos.id"), nullable=True)
    tipo            = Column(String(100))   # falha, sobrecarga, manutencao, vandalismo, outro
    descricao       = Column(Text, nullable=False)
    status          = Column(String(50), default="aberto")  # aberto, em_andamento, resolvido, cancelado
    resolucao       = Column(Text)
    criado_em       = Column(DateTime, default=datetime.utcnow)
    resolvido_em    = Column(DateTime)
    usuario         = relationship("Usuario", backref="incidentes")
    eletroposto     = relationship("Eletroposto", back_populates="incidentes")

class GeracaoSolar(Base):
    __tablename__ = "geracao_solar"
    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id   = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    mes_ano      = Column(String(10), nullable=False)   # ex: "05/2026"
    consumo_kwh  = Column(Float, default=0)
    geracao_kwh  = Column(Float, default=0)
    saldo_kwh    = Column(Float, default=0)
    criado_em    = Column(DateTime, default=datetime.utcnow)
    usuario      = relationship("Usuario", backref="geracao_solar")

def criar_tabelas_ev():
    Base.metadata.create_all(bind=engine)
    print("Tabelas EV criadas com sucesso.")
