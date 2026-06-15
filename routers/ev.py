from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models.connection import get_db
from models.ev_models import Eletroposto, SessaoCarregamento, Fatura, Incidente, GeracaoSolar
from models.database import Usuario
from routers.auth import get_usuario_atual
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

router = APIRouter()

# ── SCHEMAS ──

class EletropostoCreate(BaseModel):
    codigo: str
    localizacao: str
    potencia_kw: float = 7.4
    tarifa_kwh: float = 1.20
    status: str = "online"

class EletropostoUpdate(BaseModel):
    codigo: Optional[str] = None
    localizacao: Optional[str] = None
    potencia_kw: Optional[float] = None
    tarifa_kwh: Optional[float] = None
    status: Optional[str] = None

class SessaoCreate(BaseModel):
    usuario_id: UUID
    eletroposto_id: UUID
    inicio: datetime
    fim: Optional[datetime] = None
    duracao_minutos: Optional[int] = None
    energia_kwh: Optional[float] = None
    tarifa_kwh: float = 0.75
    status: str = "concluida"
    observacao: Optional[str] = None

class IncidenteCreate(BaseModel):
    eletroposto_id: Optional[UUID] = None
    usuario_id: Optional[UUID] = None
    tipo: str
    descricao: str

class IncidenteUpdate(BaseModel):
    status: str
    resolucao: Optional[str] = None

class GeracaoCreate(BaseModel):
    usuario_id: UUID
    mes_ano: str
    consumo_kwh: float
    geracao_kwh: float

# ── ELETROPOSTOS ──

@router.get("/eletropostos")
def listar_eletropostos(db: Session = Depends(get_db), _=Depends(get_usuario_atual)):
    eps = db.query(Eletroposto).all()
    return [{
        "id": str(ep.id), "codigo": ep.codigo,
        "localizacao": ep.localizacao, "potencia_kw": ep.potencia_kw,
        "tarifa_kwh": ep.tarifa_kwh, "status": ep.status, "instalado_em": ep.instalado_em
    } for ep in eps]

@router.post("/eletropostos")
def criar_eletroposto(dados: EletropostoCreate, db: Session = Depends(get_db), u=Depends(get_usuario_atual)):
    if u.perfil.nome not in ["admin", "sindico"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    ep = Eletroposto(**dados.model_dump())
    db.add(ep); db.commit(); db.refresh(ep)
    return {"id": str(ep.id), "codigo": ep.codigo}

@router.patch("/eletropostos/{ep_id}/status")
def atualizar_status(ep_id: UUID, status: str, db: Session = Depends(get_db), u=Depends(get_usuario_atual)):
    if u.perfil.nome not in ["admin", "sindico"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    ep = db.query(Eletroposto).filter(Eletroposto.id == str(ep_id)).first()
    if not ep: raise HTTPException(status_code=404, detail="Eletroposto não encontrado")
    ep.status = status; db.commit()
    return {"ok": True}

@router.patch("/eletropostos/{ep_id}")
def atualizar_eletroposto(ep_id: UUID, dados: EletropostoUpdate, db: Session = Depends(get_db), u=Depends(get_usuario_atual)):
    if u.perfil.nome not in ["admin", "sindico"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    ep = db.query(Eletroposto).filter(Eletroposto.id == str(ep_id)).first()
    if not ep: raise HTTPException(status_code=404, detail="Eletroposto não encontrado")
    if dados.codigo: ep.codigo = dados.codigo.upper()
    if dados.localizacao: ep.localizacao = dados.localizacao
    if dados.potencia_kw: ep.potencia_kw = dados.potencia_kw
    if dados.tarifa_kwh: ep.tarifa_kwh = dados.tarifa_kwh
    if dados.status: ep.status = dados.status
    db.commit()
    return {"ok": True}

# ── SESSÕES ──

@router.get("/sessoes")
def listar_sessoes(
    mes_ano: Optional[str] = None,
    usuario_id: Optional[UUID] = None,
    eletroposto_id: Optional[UUID] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    u=Depends(get_usuario_atual)
):
    q = db.query(SessaoCarregamento)
    if usuario_id:
        q = q.filter(SessaoCarregamento.usuario_id == str(usuario_id))
    if eletroposto_id:
        q = q.filter(SessaoCarregamento.eletroposto_id == str(eletroposto_id))
    if mes_ano:
        ano, mes = mes_ano.split("-") if "-" in mes_ano else (mes_ano.split("/")[1], mes_ano.split("/")[0])
        q = q.filter(
            func.extract("month", SessaoCarregamento.inicio) == int(mes),
            func.extract("year",  SessaoCarregamento.inicio) == int(ano)
        )
    sessoes = q.order_by(desc(SessaoCarregamento.inicio)).limit(limit).all()
    return [{
        "id": str(s.id),
        "apartamento": s.usuario.nome if s.usuario else "—",
        "usuario": s.usuario.username if s.usuario else "—",
        "eletroposto": s.eletroposto.codigo if s.eletroposto else "—",
        "inicio": s.inicio, "fim": s.fim,
        "duracao_minutos": s.duracao_minutos,
        "energia_kwh": s.energia_kwh,
        "tarifa_kwh": s.tarifa_kwh,
        "custo_total": s.custo_total,
        "status": s.status,
        "observacao": s.observacao
    } for s in sessoes]

@router.post("/sessoes")
def registrar_sessao(dados: SessaoCreate, db: Session = Depends(get_db), u=Depends(get_usuario_atual)):
    if u.perfil.nome not in ["admin", "sindico"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    ep = db.query(Eletroposto).filter(Eletroposto.id == str(dados.eletroposto_id)).first()
    tarifa = ep.tarifa_kwh if ep and ep.tarifa_kwh else dados.tarifa_kwh
    custo = round((dados.energia_kwh or 0) * tarifa, 2)
    sessao = SessaoCarregamento(
        usuario_id=str(dados.usuario_id),
        eletroposto_id=str(dados.eletroposto_id),
        inicio=dados.inicio, fim=dados.fim,
        duracao_minutos=dados.duracao_minutos,
        energia_kwh=dados.energia_kwh,
        tarifa_kwh=tarifa,
        custo_total=custo,
        status=dados.status,
        observacao=dados.observacao
    )
    db.add(sessao); db.flush()
    fatura = Fatura(
        sessao_id=sessao.id,
        valor=custo,
        status="pendente",
        vencimento=datetime.utcnow().replace(day=10)
    )
    db.add(fatura); db.commit()
    return {"id": str(sessao.id), "custo_total": custo, "fatura_gerada": True}

# ── RELATÓRIOS ──

@router.get("/relatorios/consumo")
def relatorio_consumo(
    mes_ano: Optional[str] = None,
    db: Session = Depends(get_db),
    u=Depends(get_usuario_atual)
):
    if u.perfil.nome not in ["admin", "sindico"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    q = db.query(
        Usuario.username,
        Usuario.nome,
        func.sum(SessaoCarregamento.energia_kwh).label("total_kwh"),
        func.sum(SessaoCarregamento.custo_total).label("total_custo"),
        func.count(SessaoCarregamento.id).label("total_sessoes"),
        func.sum(SessaoCarregamento.duracao_minutos).label("total_minutos")
    ).join(SessaoCarregamento, SessaoCarregamento.usuario_id == Usuario.id)
    if mes_ano:
        mes, ano = mes_ano.split("/")
        q = q.filter(
            func.extract("month", SessaoCarregamento.inicio) == int(mes),
            func.extract("year",  SessaoCarregamento.inicio) == int(ano)
        )
    resultado = q.group_by(Usuario.id, Usuario.username, Usuario.nome)\
                 .order_by(desc("total_kwh")).all()
    return [{
        "usuario": r.username, "nome": r.nome,
        "total_kwh": round(r.total_kwh or 0, 2),
        "total_custo": round(r.total_custo or 0, 2),
        "total_sessoes": r.total_sessoes,
        "total_minutos": r.total_minutos or 0
    } for r in resultado]

@router.get("/relatorios/inadimplencia")
def relatorio_inadimplencia(db: Session = Depends(get_db), u=Depends(get_usuario_atual)):
    if u.perfil.nome not in ["admin", "sindico"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    faturas = db.query(Fatura).filter(
        Fatura.status.in_(["pendente", "inadimplente"])
    ).order_by(desc(Fatura.vencimento)).all()
    return [{
        "fatura_id": str(f.id),
        "usuario": f.sessao.usuario.username if f.sessao and f.sessao.usuario else "—",
        "nome": f.sessao.usuario.nome if f.sessao and f.sessao.usuario else "—",
        "valor": f.valor,
        "status": f.status,
        "vencimento": f.vencimento,
        "energia_kwh": f.sessao.energia_kwh if f.sessao else 0
    } for f in faturas]

@router.get("/relatorios/eletropostos")
def relatorio_eletropostos(db: Session = Depends(get_db), u=Depends(get_usuario_atual)):
    if u.perfil.nome not in ["admin", "sindico"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    resultado = db.query(
        Eletroposto.codigo, Eletroposto.localizacao, Eletroposto.status,
        func.count(SessaoCarregamento.id).label("total_sessoes"),
        func.sum(SessaoCarregamento.energia_kwh).label("total_kwh"),
        func.sum(SessaoCarregamento.duracao_minutos).label("total_minutos")
    ).outerjoin(SessaoCarregamento)\
     .group_by(Eletroposto.id)\
     .order_by(desc("total_kwh")).all()
    return [{
        "codigo": r.codigo, "localizacao": r.localizacao, "status": r.status,
        "total_sessoes": r.total_sessoes or 0,
        "total_kwh": round(r.total_kwh or 0, 2),
        "total_minutos": r.total_minutos or 0
    } for r in resultado]

# ── FATURAS ──

@router.get("/faturas")
def listar_faturas(status: Optional[str] = None, db: Session = Depends(get_db), u=Depends(get_usuario_atual)):
    q = db.query(Fatura)
    if status:
        q = q.filter(Fatura.status == status)
    faturas = q.order_by(desc(Fatura.criado_em)).all()
    return [{
        "id": str(f.id),
        "usuario": f.sessao.usuario.username if f.sessao and f.sessao.usuario else "—",
        "valor": f.valor, "status": f.status,
        "vencimento": f.vencimento, "pago_em": f.pago_em
    } for f in faturas]

@router.patch("/faturas/{fatura_id}/pagar")
def marcar_pago(fatura_id: UUID, db: Session = Depends(get_db), u=Depends(get_usuario_atual)):
    if u.perfil.nome not in ["admin", "sindico"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    f = db.query(Fatura).filter(Fatura.id == str(fatura_id)).first()
    if not f: raise HTTPException(status_code=404, detail="Fatura não encontrada")
    f.status = "pago"; f.pago_em = datetime.utcnow(); db.commit()
    return {"ok": True}

# ── INCIDENTES ──

@router.get("/incidentes")
def listar_incidentes(status: Optional[str] = None, db: Session = Depends(get_db), u=Depends(get_usuario_atual)):
    q = db.query(Incidente)
    if status:
        q = q.filter(Incidente.status == status)
    incidentes = q.order_by(desc(Incidente.criado_em)).all()
    return [{
        "id": str(i.id),
        "eletroposto": i.eletroposto.codigo if i.eletroposto else "—",
        "usuario": i.usuario.username if i.usuario else "—",
        "tipo": i.tipo, "descricao": i.descricao,
        "status": i.status, "resolucao": i.resolucao,
        "criado_em": i.criado_em, "resolvido_em": i.resolvido_em
    } for i in incidentes]

@router.post("/incidentes")
def abrir_incidente(dados: IncidenteCreate, db: Session = Depends(get_db), u=Depends(get_usuario_atual)):
    inc = Incidente(
        eletroposto_id=str(dados.eletroposto_id) if dados.eletroposto_id else None,
        usuario_id=str(dados.usuario_id) if dados.usuario_id else str(u.id),
        tipo=dados.tipo, descricao=dados.descricao
    )
    db.add(inc); db.commit()
    return {"id": str(inc.id), "status": "aberto"}

@router.patch("/incidentes/{inc_id}")
def atualizar_incidente(inc_id: UUID, dados: IncidenteUpdate, db: Session = Depends(get_db), u=Depends(get_usuario_atual)):
    if u.perfil.nome not in ["admin", "sindico"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    inc = db.query(Incidente).filter(Incidente.id == str(inc_id)).first()
    if not inc: raise HTTPException(status_code=404, detail="Incidente não encontrado")
    inc.status = dados.status
    if dados.resolucao: inc.resolucao = dados.resolucao
    if dados.status == "resolvido": inc.resolvido_em = datetime.utcnow()
    db.commit()
    return {"ok": True}

# ── GERAÇÃO SOLAR ──

@router.post("/solar")
def registrar_geracao(dados: GeracaoCreate, db: Session = Depends(get_db), u=Depends(get_usuario_atual)):
    if u.perfil.nome not in ["admin", "sindico"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    saldo = round(dados.geracao_kwh - dados.consumo_kwh, 2)
    g = GeracaoSolar(
        usuario_id=str(dados.usuario_id),
        mes_ano=dados.mes_ano,
        consumo_kwh=dados.consumo_kwh,
        geracao_kwh=dados.geracao_kwh,
        saldo_kwh=saldo
    )
    db.add(g); db.commit()
    return {"id": str(g.id), "saldo_kwh": saldo}

@router.get("/solar")
def listar_geracao(mes_ano: Optional[str] = None, db: Session = Depends(get_db), u=Depends(get_usuario_atual)):
    q = db.query(GeracaoSolar)
    if mes_ano:
        q = q.filter(GeracaoSolar.mes_ano == mes_ano)
    return [{
        "usuario": g.usuario.username if g.usuario else "—",
        "nome": g.usuario.nome if g.usuario else "—",
        "mes_ano": g.mes_ano,
        "consumo_kwh": g.consumo_kwh,
        "geracao_kwh": g.geracao_kwh,
        "saldo_kwh": g.saldo_kwh
    } for g in q.all()]
