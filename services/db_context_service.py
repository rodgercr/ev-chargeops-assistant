"""
db_context_service.py
Busca dados reais do PostgreSQL e monta um contexto estruturado
para o LLaMA responder com informações precisas.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models.database import Usuario
from models.ev_models import (
    Eletroposto, SessaoCarregamento, Fatura, Incidente, GeracaoSolar
)
from datetime import datetime


def contexto_sindico(db: Session, pergunta: str) -> str:
    """
    Analisa a pergunta e busca os dados mais relevantes do banco.
    Retorna um bloco de texto estruturado para injetar no prompt.
    """
    partes = []
    pergunta_lower = pergunta.lower()

    # ── SESSÕES / CONSUMO ──
    if any(w in pergunta_lower for w in [
        "consumo", "carregou", "kwh", "sessão", "sessao", "usou",
        "mais usou", "mais consumiu", "carregamento", "energia"
    ]):
        partes.append(_consumo_por_usuario(db))
        partes.append(_consumo_por_eletroposto(db))

    # ── ELETROPOSTOS ──
    if any(w in pergunta_lower for w in [
        "eletroposto", "carregador", "ep-", "status", "offline",
        "online", "manutenção", "manutencao", "falha"
    ]):
        partes.append(_status_eletropostos(db))

    # ── INCIDENTES ──
    if any(w in pergunta_lower for w in [
        "incidente", "falha", "problema", "erro", "pendente",
        "aberto", "resolvido", "suporte", "chamado"
    ]):
        partes.append(_incidentes(db))

    # ── FINANCEIRO / INADIMPLÊNCIA ──
    if any(w in pergunta_lower for w in [
        "fatura", "pagar", "pagamento", "inadimpl", "cobrança",
        "cobranca", "pendente", "deve", "custo", "valor", "financeiro"
    ]):
        partes.append(_financeiro(db))

    # ── SOLAR ──
    if any(w in pergunta_lower for w in [
        "solar", "geração", "geracao", "saldo", "crédito", "credito"
    ]):
        partes.append(_geracao_solar(db))

    # ── RESUMO GERAL (fallback) ──
    if not partes or any(w in pergunta_lower for w in [
        "resumo", "geral", "overview", "relatório", "relatorio", "tudo"
    ]):
        partes = [
            _consumo_por_usuario(db),
            _status_eletropostos(db),
            _incidentes(db),
            _financeiro(db),
        ]

    return "\n\n".join(filter(None, partes))


def contexto_morador(db: Session, pergunta: str, usuario_id) -> str:
    """Monta contexto somente com dados pertencentes ao morador autenticado."""
    if not usuario_id:
        return "DADOS DO MORADOR: Usuário não identificado."

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if usuario is None:
        return "DADOS DO MORADOR: Usuário não encontrado."

    pergunta_lower = pergunta.lower()
    partes = [
        f"DADOS AUTORIZADOS DO MORADOR: {usuario.nome or usuario.username}. "
        "Não utilize nem solicite dados de outros moradores."
    ]
    encontrou_assunto = False

    if any(w in pergunta_lower for w in [
        "recarga", "carregamento", "consumo", "kwh", "sessão", "sessao",
        "energia", "custo", "gastei", "histórico", "historico"
    ]):
        partes.append(_recargas_do_morador(db, usuario_id))
        encontrou_assunto = True

    if any(w in pergunta_lower for w in [
        "fatura", "pagar", "pagamento", "cobrança", "cobranca", "valor",
        "pendente", "vencimento", "inadimpl"
    ]):
        partes.append(_faturas_do_morador(db, usuario_id))
        encontrou_assunto = True

    if any(w in pergunta_lower for w in [
        "solar", "geração", "geracao", "saldo", "crédito", "credito"
    ]):
        partes.append(_solar_do_morador(db, usuario_id))
        encontrou_assunto = True

    if any(w in pergunta_lower for w in [
        "incidente", "falha", "problema", "erro", "chamado", "suporte"
    ]):
        partes.append(_incidentes_do_morador(db, usuario_id))
        encontrou_assunto = True

    if any(w in pergunta_lower for w in [
        "eletroposto", "carregador", "disponível", "disponivel", "online",
        "offline", "manutenção", "manutencao", "tarifa"
    ]):
        partes.append(_status_eletropostos(db))
        encontrou_assunto = True

    if not encontrou_assunto:
        partes.extend([
            _resumo_do_morador(db, usuario_id),
            _status_eletropostos(db),
        ])

    return "\n\n".join(filter(None, partes))


def _resumo_do_morador(db: Session, usuario_id) -> str:
    total_sessoes, total_kwh, total_custo = db.query(
        func.count(SessaoCarregamento.id),
        func.sum(SessaoCarregamento.energia_kwh),
        func.sum(SessaoCarregamento.custo_total),
    ).filter(SessaoCarregamento.usuario_id == usuario_id).one()
    return (
        "RESUMO DO MORADOR: "
        f"{total_sessoes or 0} recargas | "
        f"{total_kwh or 0:.1f} kWh | R$ {total_custo or 0:.2f}."
    )


def _recargas_do_morador(db: Session, usuario_id) -> str:
    sessoes = db.query(SessaoCarregamento)\
        .filter(SessaoCarregamento.usuario_id == usuario_id)\
        .order_by(desc(SessaoCarregamento.inicio))\
        .limit(20).all()

    if not sessoes:
        return "RECARGAS DO MORADOR: Nenhuma sessão registrada."

    linhas = ["RECARGAS DO MORADOR (somente do usuário autenticado):"]
    for sessao in sessoes:
        eletroposto = sessao.eletroposto.codigo if sessao.eletroposto else "—"
        inicio = sessao.inicio.strftime("%d/%m/%Y %H:%M") if sessao.inicio else "—"
        linhas.append(
            f"- {inicio} | {eletroposto} | {sessao.energia_kwh or 0:.1f} kWh | "
            f"R$ {sessao.custo_total or 0:.2f} | Status: {sessao.status}."
        )
    return "\n".join(linhas)


def _faturas_do_morador(db: Session, usuario_id) -> str:
    faturas = db.query(Fatura)\
        .join(SessaoCarregamento, Fatura.sessao_id == SessaoCarregamento.id)\
        .filter(SessaoCarregamento.usuario_id == usuario_id)\
        .order_by(desc(Fatura.criado_em))\
        .limit(20).all()

    if not faturas:
        return "FATURAS DO MORADOR: Nenhuma fatura registrada."

    linhas = ["FATURAS DO MORADOR (somente do usuário autenticado):"]
    for fatura in faturas:
        vencimento = (
            fatura.vencimento.strftime("%d/%m/%Y") if fatura.vencimento else "—"
        )
        linhas.append(
            f"- R$ {fatura.valor:.2f} | Status: {fatura.status} | "
            f"Vencimento: {vencimento}."
        )
    return "\n".join(linhas)


def _solar_do_morador(db: Session, usuario_id) -> str:
    registros = db.query(GeracaoSolar)\
        .filter(GeracaoSolar.usuario_id == usuario_id)\
        .order_by(desc(GeracaoSolar.mes_ano))\
        .limit(20).all()

    if not registros:
        return "GERAÇÃO SOLAR DO MORADOR: Nenhum registro encontrado."

    linhas = ["GERAÇÃO SOLAR DO MORADOR (somente do usuário autenticado):"]
    for registro in registros:
        linhas.append(
            f"- {registro.mes_ano}: consumo {registro.consumo_kwh or 0:.1f} kWh | "
            f"geração {registro.geracao_kwh or 0:.1f} kWh | "
            f"saldo {registro.saldo_kwh or 0:.1f} kWh."
        )
    return "\n".join(linhas)


def _incidentes_do_morador(db: Session, usuario_id) -> str:
    incidentes = db.query(Incidente)\
        .filter(Incidente.usuario_id == usuario_id)\
        .order_by(desc(Incidente.criado_em))\
        .limit(20).all()

    if not incidentes:
        return "INCIDENTES DO MORADOR: Nenhum incidente registrado."

    linhas = ["INCIDENTES DO MORADOR (somente do usuário autenticado):"]
    for incidente in incidentes:
        eletroposto = incidente.eletroposto.codigo if incidente.eletroposto else "—"
        data = incidente.criado_em.strftime("%d/%m/%Y") if incidente.criado_em else "—"
        linhas.append(
            f"- {data} | {eletroposto} | {incidente.tipo} | "
            f"Status: {incidente.status} | {incidente.descricao}."
        )
    return "\n".join(linhas)


def _consumo_por_usuario(db: Session) -> str:
    resultado = db.query(
        Usuario.username,
        Usuario.nome,
        func.sum(SessaoCarregamento.energia_kwh).label("total_kwh"),
        func.sum(SessaoCarregamento.custo_total).label("total_custo"),
        func.count(SessaoCarregamento.id).label("total_sessoes"),
        func.sum(SessaoCarregamento.duracao_minutos).label("total_minutos")
    ).join(SessaoCarregamento, SessaoCarregamento.usuario_id == Usuario.id)\
     .group_by(Usuario.id, Usuario.username, Usuario.nome)\
     .order_by(desc("total_kwh")).all()

    if not resultado:
        return "CONSUMO POR USUÁRIO: Nenhuma sessão registrada."

    linhas = ["CONSUMO POR USUÁRIO (todos os períodos):"]
    for r in resultado:
        linhas.append(
            f"- {r.nome} ({r.username}): {r.total_kwh:.1f} kWh | "
            f"{r.total_sessoes} sessões | "
            f"{r.total_minutos or 0} min | "
            f"R$ {r.total_custo:.2f}"
        )
    return "\n".join(linhas)


def _consumo_por_eletroposto(db: Session) -> str:
    resultado = db.query(
        Eletroposto.codigo,
        Eletroposto.localizacao,
        func.count(SessaoCarregamento.id).label("total_sessoes"),
        func.sum(SessaoCarregamento.energia_kwh).label("total_kwh"),
        func.sum(SessaoCarregamento.duracao_minutos).label("total_minutos")
    ).outerjoin(SessaoCarregamento)\
     .group_by(Eletroposto.id)\
     .order_by(desc("total_kwh")).all()

    if not resultado:
        return ""

    linhas = ["CONSUMO POR ELETROPOSTO:"]
    for r in resultado:
        linhas.append(
            f"- {r.codigo} ({r.localizacao}): "
            f"{r.total_sessoes or 0} sessões | "
            f"{r.total_kwh or 0:.1f} kWh | "
            f"{r.total_minutos or 0} min"
        )
    return "\n".join(linhas)


def _status_eletropostos(db: Session) -> str:
    eps = db.query(Eletroposto).order_by(Eletroposto.codigo).all()
    if not eps:
        return "ELETROPOSTOS: Nenhum cadastrado."

    linhas = ["STATUS DOS ELETROPOSTOS:"]
    for ep in eps:
        linhas.append(
            f"- {ep.codigo} | {ep.localizacao} | "
            f"Potência: {ep.potencia_kw} kW | "
            f"Tarifa: R$ {ep.tarifa_kwh or 0:.2f}/kWh | "
            f"Status: {ep.status.upper()}"
        )
    return "\n".join(linhas)


def _incidentes(db: Session) -> str:
    incidentes = db.query(Incidente)\
        .order_by(desc(Incidente.criado_em))\
        .limit(20).all()

    if not incidentes:
        return "INCIDENTES: Nenhum registrado."

    abertos = [i for i in incidentes if i.status in ["aberto", "em_andamento"]]
    linhas = [f"INCIDENTES ({len(incidentes)} total, {len(abertos)} pendentes):"]

    for i in incidentes:
        ep = i.eletroposto.codigo if i.eletroposto else "Área comum"
        data = i.criado_em.strftime("%d/%m/%Y") if i.criado_em else "—"
        linhas.append(
            f"- [{i.status.upper()}] {ep} | {i.tipo} | {data}: "
            f"{i.descricao}"
            + (f" → Resolução: {i.resolucao}" if i.resolucao else "")
        )
    return "\n".join(linhas)


def _financeiro(db: Session) -> str:
    faturas = db.query(Fatura)\
        .order_by(desc(Fatura.criado_em))\
        .limit(50).all()

    if not faturas:
        return "FINANCEIRO: Nenhuma fatura registrada."

    pendentes = [f for f in faturas if f.status == "pendente"]
    pagas     = [f for f in faturas if f.status == "pago"]
    total_pend = sum(f.valor for f in pendentes)
    total_pago = sum(f.valor for f in pagas)

    linhas = [
        f"FINANCEIRO: {len(faturas)} faturas | "
        f"Pendentes: {len(pendentes)} (R$ {total_pend:.2f}) | "
        f"Pagas: {len(pagas)} (R$ {total_pago:.2f})"
    ]
    if pendentes:
        linhas.append("Faturas pendentes:")
        for f in pendentes[:10]:
            usuario = f.sessao.usuario.nome if f.sessao and f.sessao.usuario else "—"
            linhas.append(f"  - {usuario}: R$ {f.valor:.2f} | Venc: {f.vencimento.strftime('%d/%m/%Y') if f.vencimento else '—'}")

    return "\n".join(linhas)


def _geracao_solar(db: Session) -> str:
    registros = db.query(GeracaoSolar)\
        .order_by(desc(GeracaoSolar.mes_ano))\
        .all()

    if not registros:
        return "GERAÇÃO SOLAR: Nenhum registro."

    linhas = ["GERAÇÃO SOLAR POR USUÁRIO:"]
    for g in registros:
        nome = g.usuario.nome if g.usuario else "—"
        saldo_txt = f"+{g.saldo_kwh:.1f} kWh (crédito)" if g.saldo_kwh > 0 else f"{g.saldo_kwh:.1f} kWh (déficit)"
        linhas.append(
            f"- {nome} | {g.mes_ano}: "
            f"Consumo {g.consumo_kwh} kWh | "
            f"Geração {g.geracao_kwh} kWh | "
            f"Saldo: {saldo_txt}"
        )
    return "\n".join(linhas)
