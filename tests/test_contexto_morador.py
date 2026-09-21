from datetime import datetime
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, Perfil, Usuario
from models.ev_models import Eletroposto, Fatura, GeracaoSolar, SessaoCarregamento
from services.db_context_service import contexto_morador


def criar_banco_teste():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_contexto_morador_isola_dados_por_usuario() -> None:
    db = criar_banco_teste()
    perfil = Perfil(id=uuid.uuid4(), nome="morador", descricao="Morador")
    alice = Usuario(
        id=uuid.uuid4(),
        username="alice",
        nome="Alice",
        senha_hash="teste",
        perfil=perfil,
    )
    bob = Usuario(
        id=uuid.uuid4(),
        username="bob",
        nome="Bob",
        senha_hash="teste",
        perfil=perfil,
    )
    ep = Eletroposto(
        id=uuid.uuid4(), codigo="EP-01", localizacao="Garagem", status="online"
    )
    sessao_alice = SessaoCarregamento(
        id=uuid.uuid4(),
        usuario=alice,
        eletroposto=ep,
        inicio=datetime(2026, 9, 20, 10, 0),
        energia_kwh=10.0,
        custo_total=12.5,
        status="concluida",
    )
    sessao_bob = SessaoCarregamento(
        id=uuid.uuid4(),
        usuario=bob,
        eletroposto=ep,
        inicio=datetime(2026, 9, 20, 11, 0),
        energia_kwh=99.0,
        custo_total=123.45,
        status="concluida",
    )
    db.add_all(
        [
            perfil,
            alice,
            bob,
            ep,
            sessao_alice,
            sessao_bob,
            Fatura(
                id=uuid.uuid4(),
                sessao=sessao_alice,
                valor=12.5,
                status="pendente",
            ),
            Fatura(
                id=uuid.uuid4(),
                sessao=sessao_bob,
                valor=123.45,
                status="pendente",
            ),
            GeracaoSolar(
                id=uuid.uuid4(),
                usuario=alice,
                mes_ano="09/2026",
                consumo_kwh=10.0,
                geracao_kwh=8.0,
                saldo_kwh=-2.0,
            ),
        ]
    )
    db.commit()

    contexto = contexto_morador(
        db,
        "Mostre minhas recargas, minha fatura e meu saldo solar",
        alice.id,
    )

    assert "Alice" in contexto
    assert "10.0 kWh" in contexto
    assert "R$ 12.50" in contexto
    assert "09/2026" in contexto
    assert "Bob" not in contexto
    assert "99.0 kWh" not in contexto
    assert "R$ 123.45" not in contexto
    db.close()


def test_contexto_morador_sem_usuario_nao_consulta_dados() -> None:
    db = criar_banco_teste()
    assert contexto_morador(db, "minhas recargas", None) == (
        "DADOS DO MORADOR: Usuário não identificado."
    )
    db.close()
