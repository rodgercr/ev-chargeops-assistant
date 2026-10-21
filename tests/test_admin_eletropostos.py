"""Integração em SQLite isolado: nunca grava no PostgreSQL do usuário."""
from datetime import date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.database import Base, Perfil, Usuario
from models.ev_models import Eletroposto, SessaoCarregamento, Fatura
from services.admin_eletropostos import (
    DadosEletroposto, CodigoEmUso, EdicaoDesatualizada, exigir_admin,
    listar_eletropostos, criar_eletroposto, atualizar_eletroposto, historico_carregador,
)


@pytest.fixture
def ambiente_admin():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    db = factory()
    usuarios = {}
    for nome in ("admin", "sindico", "morador"):
        perfil = Perfil(nome=nome)
        usuario = Usuario(username=f"teste_{nome}", nome=nome, senha_hash="hash-teste", ativo=True, perfil=perfil)
        db.add(usuario)
        db.flush()
        usuarios[nome] = usuario.id
    posto = Eletroposto(codigo="EP-01", localizacao="Garagem A", potencia_kw=7.4, tarifa_kwh=1.2, status="online")
    db.add(posto)
    db.commit()
    ambiente = {"db": db, "factory": factory, "users": usuarios, "posto": posto.id}
    yield ambiente
    db.close()
    engine.dispose()


def dados_validos(**alteracoes):
    return {"codigo": " ep-02 ", "localizacao": " Garagem B ", "potencia_kw": 22,
            "tarifa_kwh": 1.5, "status": "online", **alteracoes}


@pytest.mark.parametrize("campo,valor", [
    ("codigo", ""), ("codigo", "x" * 51), ("localizacao", " "),
    ("potencia_kw", 0), ("potencia_kw", -2), ("potencia_kw", float("nan")),
    ("potencia_kw", True), ("tarifa_kwh", -1), ("tarifa_kwh", float("inf")),
    ("status", "inventado"),
])
def test_dados_invalidos(campo, valor):
    with pytest.raises(ValidationError):
        DadosEletroposto.model_validate(dados_validos(**{campo: valor}))


def test_cadastro_normaliza_e_aceita_tarifa_zero(ambiente_admin):
    a = ambiente_admin
    criado = criar_eletroposto(a["db"], a["users"]["admin"], dados_validos(tarifa_kwh=0))
    assert criado["codigo"] == "EP-02"
    assert criado["localizacao"] == "Garagem B"
    assert criado["tarifa_kwh"] == 0
    assert len(listar_eletropostos(a["db"], a["users"]["admin"])) == 2


def test_codigo_duplicado_nao_grava(ambiente_admin):
    a = ambiente_admin
    with pytest.raises(CodigoEmUso):
        criar_eletroposto(a["db"], a["users"]["admin"], dados_validos(codigo="ep-01"))
    assert a["db"].query(Eletroposto).count() == 1


@pytest.mark.parametrize("perfil", ["morador", "sindico", "inexistente"])
def test_operacoes_restritas_a_admin(ambiente_admin, perfil):
    a = ambiente_admin
    ator = a["users"].get(perfil, uuid4())
    with pytest.raises(PermissionError):
        listar_eletropostos(a["db"], ator)
    with pytest.raises(PermissionError):
        criar_eletroposto(a["db"], ator, dados_validos())
    with pytest.raises(PermissionError):
        atualizar_eletroposto(a["db"], ator, a["posto"], dados_validos(), esperado={})
    with pytest.raises(PermissionError):
        historico_carregador(a["db"], ator, a["posto"])
    assert a["db"].query(Eletroposto).count() == 1


def test_permissao_revogada_reconsultada(ambiente_admin):
    a = ambiente_admin
    exigir_admin(a["db"], a["users"]["admin"])
    with a["factory"]() as outra:
        outra.execute(update(Usuario).where(Usuario.id == a["users"]["admin"]).values(ativo=False))
        outra.commit()
    with pytest.raises(PermissionError):
        exigir_admin(a["db"], a["users"]["admin"])


def inserir_sessao(a, posto=None, inicio=datetime(2026, 9, 10, 12), status="concluida"):
    sessao = SessaoCarregamento(
        usuario_id=a["users"]["morador"], eletroposto_id=posto or a["posto"],
        inicio=inicio, energia_kwh=10, tarifa_kwh=1.2, custo_total=12, status=status,
    )
    a["db"].add(sessao)
    a["db"].flush()
    return sessao


def test_edicao_preserva_tarifas_custos_e_faturas_anteriores(ambiente_admin):
    a = ambiente_admin
    sessao = inserir_sessao(a)
    fatura = Fatura(sessao_id=sessao.id, valor=12, status="pago")
    a["db"].add(fatura)
    a["db"].commit()
    snapshot = listar_eletropostos(a["db"], a["users"]["admin"])[0]
    atualizado = atualizar_eletroposto(a["db"], a["users"]["admin"], a["posto"],
                                     dados_validos(codigo="EP-01", potencia_kw=50, tarifa_kwh=0), esperado=snapshot)
    a["db"].refresh(sessao)
    a["db"].refresh(fatura)
    assert atualizado["potencia_kw"] == 50
    assert atualizado["tarifa_kwh"] == 0
    assert sessao.tarifa_kwh == 1.2 and sessao.custo_total == 12
    assert fatura.valor == 12 and fatura.status == "pago"


def test_detecta_edicao_concorrente(ambiente_admin):
    a = ambiente_admin
    snapshot = listar_eletropostos(a["db"], a["users"]["admin"])[0]
    atualizado = atualizar_eletroposto(a["db"], a["users"]["admin"], a["posto"],
                                     dados_validos(codigo="EP-01", tarifa_kwh=2), esperado=snapshot)
    with pytest.raises(EdicaoDesatualizada):
        atualizar_eletroposto(a["db"], a["users"]["admin"], a["posto"],
                             dados_validos(codigo="EP-01", tarifa_kwh=5), esperado=snapshot)
    assert listar_eletropostos(a["db"], a["users"]["admin"])[0] == atualizado


def test_edicao_rejeita_outro_codigo_e_posto_inexistente(ambiente_admin):
    a = ambiente_admin
    criar_eletroposto(a["db"], a["users"]["admin"], dados_validos())
    snapshot = listar_eletropostos(a["db"], a["users"]["admin"])[0]
    with pytest.raises(CodigoEmUso):
        atualizar_eletroposto(a["db"], a["users"]["admin"], a["posto"], dados_validos(), esperado=snapshot)
    with pytest.raises(LookupError):
        atualizar_eletroposto(a["db"], a["users"]["admin"], uuid4(), dados_validos(), esperado=snapshot)


def test_historico_filtra_posto_periodo_e_status(ambiente_admin):
    a = ambiente_admin
    outro = Eletroposto(codigo="EP-OUTRO")
    a["db"].add(outro)
    a["db"].flush()
    inserir_sessao(a, inicio=datetime(2026, 9, 10, 23, 59, 59))
    inserir_sessao(a, inicio=datetime(2026, 9, 11))
    inserir_sessao(a, inicio=datetime(2026, 9, 10), status="cancelada")
    inserir_sessao(a, posto=outro.id, inicio=datetime(2026, 9, 10))
    a["db"].commit()
    result = historico_carregador(a["db"], a["users"]["admin"], a["posto"],
                                 inicio=date(2026, 9, 10), fim=date(2026, 9, 10), status="concluida")
    assert result["total"] == 1
    assert result["energia_kwh"] == 10 and result["custo_total"] == 12
    assert result["registros"][0]["inicio"].hour == 23
    assert result["registros"][0]["tarifa_kwh"] == 1.2


def test_paginacao_total_e_vazio(ambiente_admin):
    a = ambiente_admin
    for dia in range(1, 28):
        inserir_sessao(a, inicio=datetime(2026, 9, dia))
    a["db"].commit()
    pagina1 = historico_carregador(a["db"], a["users"]["admin"], a["posto"])
    pagina2 = historico_carregador(a["db"], a["users"]["admin"], a["posto"], pagina=2)
    assert pagina1["total"] == pagina2["total"] == 27
    assert pagina1["energia_kwh"] == pagina2["energia_kwh"] == 270
    assert len(pagina1["registros"]) == 25 and len(pagina2["registros"]) == 2
    assert not {s["id"] for s in pagina1["registros"]} & {s["id"] for s in pagina2["registros"]}
    vazio = historico_carregador(a["db"], a["users"]["admin"], a["posto"], status="erro")
    assert vazio["total"] == 0 and vazio["registros"] == []


def test_rejeita_filtros_invalidos(ambiente_admin):
    a = ambiente_admin
    for filtro in ({"inicio": date(2026, 9, 12), "fim": date(2026, 9, 10)}, {"pagina": 0}, {"por_pagina": 101}, {"status": "invalido"}):
        with pytest.raises(ValueError):
            historico_carregador(a["db"], a["users"]["admin"], a["posto"], **filtro)


def test_falha_de_commit_desfaz_gravacao(ambiente_admin, monkeypatch):
    a = ambiente_admin
    def falhar():
        raise SQLAlchemyError("falha simulada")
    monkeypatch.setattr(a["db"], "commit", falhar)
    with pytest.raises(SQLAlchemyError):
        criar_eletroposto(a["db"], a["users"]["admin"], dados_validos())
    assert a["db"].query(Eletroposto).count() == 1


def test_api_registro_de_recarga_respeita_tarifa_zero():
    from types import SimpleNamespace
    from unittest.mock import Mock
    from routers.ev import SessaoCreate, registrar_sessao

    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(tarifa_kwh=0.0)
    dados = SessaoCreate(usuario_id=uuid4(), eletroposto_id=uuid4(),
                        inicio=datetime(2026, 9, 10), energia_kwh=10, tarifa_kwh=5)
    resultado = registrar_sessao(dados, db, SimpleNamespace(perfil=SimpleNamespace(nome="admin")))
    objetos = [chamada.args[0] for chamada in db.add.call_args_list]
    sessao = next(obj for obj in objetos if isinstance(obj, SessaoCarregamento))
    fatura = next(obj for obj in objetos if isinstance(obj, Fatura))
    assert sessao.tarifa_kwh == 0 and sessao.custo_total == 0
    assert fatura.valor == 0 and resultado["custo_total"] == 0
