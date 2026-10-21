"""Administração de carregadores: validação, autorização e transações."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
import logging
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import joinedload

from models.database import Usuario
from models.ev_models import Eletroposto, SessaoCarregamento

logger = logging.getLogger(__name__)
STATUS_POSTO = ("online", "offline", "manutencao", "falha")
STATUS_SESSAO = ("em_andamento", "concluida", "cancelada", "erro")
CAMPOS_POSTO = ("codigo", "localizacao", "potencia_kw", "tarifa_kwh", "status")


class DadosEletroposto(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)
    codigo: str = Field(min_length=1, max_length=50)
    localizacao: str = Field(min_length=1, max_length=200)
    potencia_kw: float = Field(gt=0)
    tarifa_kwh: float = Field(ge=0)
    status: Literal["online", "offline", "manutencao", "falha"] = "online"

    @field_validator("codigo", mode="before")
    @classmethod
    def normalizar_codigo(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("potencia_kw", "tarifa_kwh", mode="before")
    @classmethod
    def rejeitar_booleano(cls, value):
        if isinstance(value, bool):
            raise ValueError("Informe um número")
        return value


class CodigoEmUso(ValueError):
    pass


class EdicaoDesatualizada(ValueError):
    pass


def exigir_admin(db, usuario_id):
    """Revalida usuário/perfil no banco, sem confiar no perfil guardado na tela."""
    try:
        identificador = UUID(str(usuario_id))
    except (ValueError, TypeError, AttributeError):
        raise PermissionError("Acesso restrito a administradores ativos.") from None
    usuario = (
        db.query(Usuario).options(joinedload(Usuario.perfil))
        .filter(Usuario.id == identificador).populate_existing().first()
    )
    if not usuario or not usuario.ativo or not usuario.perfil or usuario.perfil.nome != "admin":
        raise PermissionError("Acesso restrito a administradores ativos.")
    return usuario


def serializar_posto(posto):
    return {"id": str(posto.id), **{campo: getattr(posto, campo) for campo in CAMPOS_POSTO}}


def listar_eletropostos(db, usuario_id):
    exigir_admin(db, usuario_id)
    return [serializar_posto(p) for p in db.query(Eletroposto).order_by(Eletroposto.codigo).all()]


def _validar_codigo_unico(db, codigo, excluir_id=None):
    consulta = db.query(Eletroposto).filter(func.upper(Eletroposto.codigo) == codigo)
    if excluir_id is not None:
        consulta = consulta.filter(Eletroposto.id != excluir_id)
    if consulta.first():
        raise CodigoEmUso("Já existe um carregador com esse código.")


def criar_eletroposto(db, usuario_id, dados: dict):
    exigir_admin(db, usuario_id)
    valores = DadosEletroposto.model_validate(dados).model_dump()
    try:
        _validar_codigo_unico(db, valores["codigo"])
        posto = Eletroposto(**valores)
        db.add(posto)
        db.flush()
        resultado = serializar_posto(posto)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise CodigoEmUso("Não foi possível cadastrar: o código já está em uso.") from None
    except (SQLAlchemyError, ValueError):
        db.rollback()
        raise
    logger.info("Carregador criado: usuario=%s eletroposto=%s", usuario_id, resultado["id"])
    return resultado


def atualizar_eletroposto(db, usuario_id, eletroposto_id, dados: dict, *, esperado: dict):
    exigir_admin(db, usuario_id)
    valores = DadosEletroposto.model_validate(dados).model_dump()
    try:
        posto = (
            db.query(Eletroposto).filter(Eletroposto.id == UUID(str(eletroposto_id)))
            .populate_existing().with_for_update().first()
        )
        if posto is None:
            raise LookupError("Carregador não encontrado.")
        # Impede sobrescrever silenciosamente mudanças feitas em outra aba/conta.
        if any(getattr(posto, campo) != esperado.get(campo) for campo in CAMPOS_POSTO):
            raise EdicaoDesatualizada("O carregador foi alterado por outra sessão. Recarregue os dados antes de salvar.")
        _validar_codigo_unico(db, valores["codigo"], posto.id)
        for campo, valor in valores.items():
            setattr(posto, campo, valor)
        db.flush()
        resultado = serializar_posto(posto)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise CodigoEmUso("Não foi possível salvar: o código já está em uso.") from None
    except (SQLAlchemyError, ValueError, LookupError):
        db.rollback()
        raise
    # Não altera SessaoCarregamento nem Fatura: preserva tarifas e custos históricos.
    logger.info("Carregador atualizado: usuario=%s eletroposto=%s", usuario_id, resultado["id"])
    return resultado


def historico_carregador(db, usuario_id, eletroposto_id, *, inicio: date | None = None,
                        fim: date | None = None, status: str | None = None,
                        pagina: int = 1, por_pagina: int = 25):
    exigir_admin(db, usuario_id)
    if inicio and fim and inicio > fim:
        raise ValueError("A data inicial não pode ser posterior à data final.")
    if status is not None and status not in STATUS_SESSAO:
        raise ValueError("Status de recarga inválido.")
    if pagina < 1 or not 1 <= por_pagina <= 100:
        raise ValueError("Paginação inválida.")
    identificador = UUID(str(eletroposto_id))
    if not db.get(Eletroposto, identificador):
        raise LookupError("Carregador não encontrado.")
    filtros = [SessaoCarregamento.eletroposto_id == identificador]
    if inicio:
        filtros.append(SessaoCarregamento.inicio >= datetime.combine(inicio, time.min))
    if fim:
        # Intervalo semiaberto inclui todo o último dia.
        filtros.append(SessaoCarregamento.inicio < datetime.combine(fim + timedelta(days=1), time.min))
    if status:
        filtros.append(SessaoCarregamento.status == status)
    total, energia, custo = db.query(
        func.count(SessaoCarregamento.id),
        func.coalesce(func.sum(SessaoCarregamento.energia_kwh), 0),
        func.coalesce(func.sum(SessaoCarregamento.custo_total), 0),
    ).filter(*filtros).one()
    registros = (
        db.query(SessaoCarregamento).options(joinedload(SessaoCarregamento.usuario))
        .filter(*filtros)
        .order_by(SessaoCarregamento.inicio.desc(), SessaoCarregamento.id.desc())
        .offset((pagina - 1) * por_pagina).limit(por_pagina).all()
    )
    return {
        "total": total, "energia_kwh": float(energia), "custo_total": float(custo),
        "pagina": pagina, "por_pagina": por_pagina,
        "registros": [{
            "id": str(s.id), "usuario": s.usuario.username if s.usuario else "—",
            "inicio": s.inicio, "fim": s.fim, "duracao_minutos": s.duracao_minutos,
            "energia_kwh": s.energia_kwh, "tarifa_kwh": s.tarifa_kwh,
            "custo_total": s.custo_total, "status": s.status,
        } for s in registros],
    }
