"""
setup_ev.py
Cria as tabelas de EV no banco e insere dados de exemplo.
Execute APÓS o setup_banco.py:
    python setup_ev.py
"""

from models.connection import engine, SessionLocal
from models.database import Base, Usuario
from models.ev_models import Eletroposto, SessaoCarregamento, Fatura, Incidente, GeracaoSolar, criar_tabelas_ev
from datetime import datetime, timedelta
import random
from sqlalchemy import text


def garantir_schema_ev() -> None:
    """Atualiza tabelas EV existentes sem apagar os dados cadastrados."""
    with engine.begin() as conexao:
        conexao.execute(
            text(
                """
                ALTER TABLE eletropostos
                ADD COLUMN IF NOT EXISTS tarifa_kwh DOUBLE PRECISION
                """
            )
        )
        conexao.execute(
            text(
                """
                UPDATE eletropostos
                SET tarifa_kwh = 1.20
                WHERE tarifa_kwh IS NULL
                """
            )
        )
        conexao.execute(
            text(
                """
                ALTER TABLE eletropostos
                ALTER COLUMN tarifa_kwh SET DEFAULT 1.20
                """
            )
        )
    print("Schema EV verificado: tarifa dos eletropostos disponível.")

def setup():
    print("Criando tabelas EV...")
    criar_tabelas_ev()
    garantir_schema_ev()

    db = SessionLocal()

    # ── ELETROPOSTOS ──
    eletropostos_dados = [
        ("EP-01", "Garagem A - Vaga 01", 7.4, "online"),
        ("EP-02", "Garagem A - Vaga 02", 7.4, "online"),
        ("EP-03", "Garagem B - Vaga 15", 22.0, "online"),
        ("EP-04", "Garagem B - Vaga 16", 22.0, "manutencao"),
        ("EP-05", "Garagem C - Vaga 30", 7.4, "online"),
    ]

    eps = {}
    for codigo, local, pot, status in eletropostos_dados:
        ep = db.query(Eletroposto).filter(Eletroposto.codigo == codigo).first()
        if not ep:
            ep = Eletroposto(codigo=codigo, localizacao=local, potencia_kw=pot, status=status)
            db.add(ep); db.flush()
            print(f"  Eletroposto criado: {codigo} — {local}")
        eps[codigo] = ep

    # ── USUÁRIOS para as sessões ──
    usuarios = db.query(Usuario).all()
    if not usuarios:
        print("  Nenhum usuário encontrado. Rode setup_banco.py primeiro.")
        db.close(); return

    # ── SESSÕES DE CARREGAMENTO ──
    print("  Criando sessões de carregamento...")
    sessoes_dados = [
        # (usuario_idx, ep_codigo, dias_atras, duracao_min, energia_kwh, tarifa)
        (0, "EP-01", 1, 45, 5.5, 0.75),
        (0, "EP-02", 3, 60, 7.4, 0.75),
        (1, "EP-03", 1, 30, 11.0, 0.75),
        (1, "EP-01", 5, 90, 22.0, 0.75),
        (2, "EP-05", 2, 42, 5.1, 0.75),
        (2, "EP-02", 7, 55, 6.8, 0.75),
        (0, "EP-03", 10, 120, 44.0, 0.75),
        (1, "EP-05", 8, 35, 4.3, 0.75),
        (2, "EP-01", 12, 50, 6.2, 0.75),
        (0, "EP-02", 15, 75, 9.2, 0.75),
    ]

    for idx, ep_cod, dias, dur, kwh, tarifa in sessoes_dados:
        u = usuarios[idx % len(usuarios)]
        ep = eps[ep_cod]
        inicio = datetime.utcnow() - timedelta(days=dias, hours=random.randint(6,22))
        fim = inicio + timedelta(minutes=dur)
        custo = round(kwh * tarifa, 2)

        sessao = SessaoCarregamento(
            usuario_id=u.id,
            eletroposto_id=ep.id,
            inicio=inicio, fim=fim,
            duracao_minutos=dur,
            energia_kwh=kwh,
            tarifa_kwh=tarifa,
            custo_total=custo,
            status="concluida"
        )
        db.add(sessao); db.flush()

        fatura = Fatura(
            sessao_id=sessao.id,
            valor=custo,
            status="pendente" if random.random() > 0.4 else "pago",
            vencimento=datetime.utcnow() + timedelta(days=10)
        )
        db.add(fatura)

    # ── INCIDENTES ──
    print("  Criando incidentes...")
    incidentes_dados = [
        ("EP-02", "falha",      "Eletroposto não inicia sessão de carregamento.",        "resolvido",   "Reinicialização remota do firmware."),
        ("EP-04", "sobrecarga", "Disjuntor desarmou durante sessão de alta potência.",   "resolvido",   "Ajuste do limite de corrente."),
        ("EP-04", "manutencao", "Revisão preventiva semestral necessária.",              "em_andamento", None),
        ("EP-01", "falha",      "Cabo do conector com desgaste visível.",                "aberto",      None),
        ("EP-03", "outro",      "Morador reportou demora para conectar.",                "resolvido",   "Limpeza do conector realizada."),
    ]

    for ep_cod, tipo, desc, status, resolucao in incidentes_dados:
        ep = eps[ep_cod]
        inc = Incidente(
            eletroposto_id=ep.id,
            tipo=tipo, descricao=desc,
            status=status, resolucao=resolucao,
            resolvido_em=datetime.utcnow() - timedelta(days=1) if status == "resolvido" else None
        )
        db.add(inc)

    # ── GERAÇÃO SOLAR ──
    print("  Criando registros de geração solar...")
    for u in usuarios[:3]:
        for mes, ano, consumo, geracao in [
            ("05", "2026", round(random.uniform(200,450), 1), round(random.uniform(150,300), 1)),
            ("04", "2026", round(random.uniform(180,400), 1), round(random.uniform(130,280), 1)),
        ]:
            g = GeracaoSolar(
                usuario_id=u.id,
                mes_ano=f"{mes}/{ano}",
                consumo_kwh=consumo,
                geracao_kwh=geracao,
                saldo_kwh=round(geracao - consumo, 1)
            )
            db.add(g)

    db.commit()
    db.close()
    print("\nSetup EV concluído!")
    print("Dados criados: 5 eletropostos, 10 sessões, 5 incidentes, geração solar.")
    print("Dados EV preparados. Agora execute o Streamlit com executar.cmd.")

if __name__ == "__main__":
    setup()
