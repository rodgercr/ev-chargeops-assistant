"""Página administrativa Streamlit; operações persistem pelo serviço autorizado."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date
import hashlib
import json
import logging
import math

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from models.connection import SessionLocal
from services.admin_eletropostos import (
    STATUS_POSTO, STATUS_SESSAO, listar_eletropostos,
    criar_eletroposto, atualizar_eletroposto, historico_carregador,
)

logger = logging.getLogger(__name__)
ROTULOS = {
    "online": "Online", "offline": "Offline", "manutencao": "Em manutenção", "falha": "Com falha",
    "em_andamento": "Em andamento", "concluida": "Concluída", "cancelada": "Cancelada", "erro": "Erro",
}


@contextmanager
def banco_admin():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def mostrar_erro(erro):
    if isinstance(erro, ValidationError):
        nomes = {"codigo": "Código", "localizacao": "Localização", "potencia_kw": "Potência",
                 "tarifa_kwh": "Tarifa", "status": "Status"}
        campos = ", ".join(dict.fromkeys(nomes.get(e["loc"][0], "Dados") for e in erro.errors()))
        st.warning(f"Revise: {campos}. Preencha os textos, use potência maior que zero e tarifa igual ou maior que zero.")
    elif isinstance(erro, (PermissionError, LookupError, ValueError)):
        st.warning(str(erro))
    else:
        logger.exception("Falha no painel de carregadores")
        st.error("Não foi possível concluir a operação. Verifique a conexão com o PostgreSQL e tente novamente.")


def campos_posto(prefixo, valores=None):
    valores = valores or {}
    a, b = st.columns([1, 2])
    codigo = a.text_input("Código do carregador", value=valores.get("codigo", ""), max_chars=50, key=f"{prefixo}_codigo", placeholder="EP-06")
    localizacao = b.text_input("Localização", value=valores.get("localizacao") or "", max_chars=200, key=f"{prefixo}_local", placeholder="Garagem B · Vaga 12")
    a, b, c = st.columns(3)
    potencia = a.number_input("Potência (kW)", min_value=0.01, value=max(float(valores.get("potencia_kw") or 7.4), 0.01), step=0.1, format="%.2f", key=f"{prefixo}_potencia")
    tarifa_atual = valores.get("tarifa_kwh")
    tarifa = b.number_input("Tarifa (R$/kWh)", min_value=0.0, value=float(tarifa_atual if tarifa_atual is not None else 1.2), step=0.01, format="%.4f", key=f"{prefixo}_tarifa")
    status_atual = valores.get("status", "online")
    status = c.selectbox("Status", STATUS_POSTO, index=STATUS_POSTO.index(status_atual) if status_atual in STATUS_POSTO else 0, format_func=ROTULOS.get, key=f"{prefixo}_status")
    if status_atual not in STATUS_POSTO:
        st.caption(f"Status legado: {status_atual}. Escolha o novo status antes de salvar.")
    return {"codigo": codigo, "localizacao": localizacao, "potencia_kw": potencia, "tarifa_kwh": tarifa, "status": status}


def aba_cadastro(usuario_id):
    revisao = st.session_state.get("admin_ep_create_version", 0)
    with st.form(f"admin_ep_create_form_{revisao}"):
        st.subheader("Novo carregador")
        st.caption("Cadastre os dados do equipamento no PostgreSQL local.")
        dados = campos_posto(f"admin_ep_create_{revisao}")
        enviar = st.form_submit_button("Cadastrar carregador", type="primary")
    if enviar:
        try:
            with banco_admin() as db:
                criado = criar_eletroposto(db, usuario_id, dados)
            st.session_state["admin_ep_create_version"] = revisao + 1
            st.session_state["admin_ep_message"] = f"Carregador {criado['codigo']} cadastrado."
            st.rerun()
        except Exception as erro:
            mostrar_erro(erro)


def aba_edicao(usuario_id, postos):
    if not postos:
        st.info("Cadastre um carregador para começar.")
        return
    por_id = {p["id"]: p for p in postos}
    selecionado = st.selectbox("Carregador para editar", list(por_id), format_func=lambda i: f"{por_id[i]['codigo']} · {por_id[i]['localizacao'] or 'Sem localização'}", key="admin_ep_edit_select")
    snapshot = st.session_state.get("admin_ep_snapshot")
    if not snapshot or snapshot["id"] != selecionado:
        st.session_state["admin_ep_snapshot"] = dict(por_id[selecionado])
        st.session_state["admin_ep_edit_revision"] = st.session_state.get("admin_ep_edit_revision", 0) + 1
    snapshot = st.session_state["admin_ep_snapshot"]
    if st.button("Recarregar dados do carregador", key="admin_ep_reload"):
        st.session_state.pop("admin_ep_snapshot", None)
        st.rerun()
    revisao = st.session_state.get("admin_ep_edit_revision", 0)
    with st.form(f"admin_ep_edit_form_{selecionado}_{revisao}"):
        st.subheader(f"Editar {snapshot['codigo']}")
        dados = campos_posto(f"admin_ep_edit_{selecionado}_{revisao}", snapshot)
        st.caption("A tarifa configurada será usada nos próximos registros de recarga. Tarifas, custos e faturas já gravados não serão recalculados. Alterar a potência aqui atualiza o cadastro, não comanda fisicamente o equipamento.")
        confirmar = st.checkbox("Confirmo a alteração dos dados deste carregador.", key=f"admin_ep_confirm_{selecionado}_{revisao}")
        salvar = st.form_submit_button("Salvar alterações", type="primary")
    if salvar:
        if not confirmar:
            st.warning("Marque a confirmação antes de salvar.")
            return
        try:
            with banco_admin() as db:
                atualizado = atualizar_eletroposto(db, usuario_id, selecionado, dados, esperado=snapshot)
            st.session_state.pop("admin_ep_snapshot", None)
            st.session_state["admin_ep_message"] = f"Carregador {atualizado['codigo']} atualizado. Histórico preservado."
            st.rerun()
        except Exception as erro:
            mostrar_erro(erro)


def aba_historico(usuario_id, postos):
    if not postos:
        st.info("Nenhum carregador cadastrado.")
        return
    por_id = {p["id"]: p for p in postos}
    a, b = st.columns([2, 1])
    escolhido = a.selectbox("Histórico do carregador", list(por_id), format_func=lambda i: por_id[i]["codigo"], key="admin_ep_history_select")
    status = b.selectbox("Status da recarga", [None, *STATUS_SESSAO], format_func=lambda s: ROTULOS.get(s, "Todos"), key="admin_ep_history_status")
    inicio = fim = None
    if st.checkbox("Filtrar por período de início da recarga", key="admin_ep_history_period"):
        a, b = st.columns(2)
        inicio = a.date_input("De", value=date.today().replace(day=1), key="admin_ep_history_start")
        fim = b.date_input("Até", value=date.today(), key="admin_ep_history_end")
    st.caption("Datas seguem o horário registrado no banco. O último dia do filtro é incluído por completo.")
    try:
        with banco_admin() as db:
            resultado = historico_carregador(db, usuario_id, escolhido, inicio=inicio, fim=fim, status=status)
        a, b, c = st.columns(3)
        a.metric("Recargas no filtro", resultado["total"])
        b.metric("Energia registrada", f"{resultado['energia_kwh']:.2f} kWh")
        c.metric("Custo registrado", f"R$ {resultado['custo_total']:.2f}")
        st.caption("Totais de todos os registros filtrados, não apenas desta página. Custo registrado não equivale a pagamentos recebidos.")
        if not resultado["total"]:
            st.info("Nenhuma recarga encontrada para este carregador e estes filtros.")
            return
        paginas = max(1, math.ceil(resultado["total"] / resultado["por_pagina"]))
        filtro_id = hashlib.sha256(json.dumps([escolhido, str(inicio), str(fim), status, paginas]).encode()).hexdigest()[:12]
        pagina = st.number_input("Página", min_value=1, max_value=paginas, value=1, step=1, key=f"admin_ep_history_page_{filtro_id}")
        if pagina != 1:
            with banco_admin() as db:
                resultado = historico_carregador(db, usuario_id, escolhido, inicio=inicio, fim=fim, status=status, pagina=pagina)
        dados = [{
            "Usuário": s["usuario"], "Início": s["inicio"], "Fim": s["fim"],
            "Duração (min)": s["duracao_minutos"], "Energia (kWh)": s["energia_kwh"],
            "Tarifa registrada (R$/kWh)": s["tarifa_kwh"], "Custo (R$)": s["custo_total"],
            "Status": ROTULOS.get(s["status"], s["status"]),
        } for s in resultado["registros"]]
        st.dataframe(pd.DataFrame(dados), hide_index=True, use_container_width=True)
        st.caption(f"Página {pagina} de {paginas} · até {resultado['por_pagina']} recargas por página")
    except Exception as erro:
        mostrar_erro(erro)


def tela_carregadores():
    usuario = st.session_state.get("usuario")
    if not usuario or usuario.get("perfil") != "admin":
        st.error("Esta página é exclusiva de administradores.")
        return
    st.markdown('<div class="admin-chargers-marker"></div>', unsafe_allow_html=True)
    st.markdown("""<style>
    .stApp:has(.admin-chargers-marker) [data-testid="stMainBlockContainer"] {
        max-width: 1120px; margin: auto; padding-top: 5.5rem;
    }
    .stApp:has(.admin-chargers-marker) [data-testid="stForm"] {
        background: var(--panel, #f7f7f8); border: 1px solid var(--line, #dcdce1);
        border-radius: 16px; padding: 1.25rem;
    }
    .stApp:has(.admin-chargers-marker) [data-testid="stMetric"] {
        background: var(--panel, #f7f7f8); border: 1px solid var(--line, #dcdce1);
        border-radius: 12px; padding: 1rem;
    }
    </style>""", unsafe_allow_html=True)
    st.title("Gerenciar carregadores")
    st.caption("Cadastro, configuração e histórico da rede de recarga.")
    try:
        with banco_admin() as db:
            postos = listar_eletropostos(db, usuario["id"])
    except Exception as erro:
        mostrar_erro(erro)
        return
    mensagem = st.session_state.pop("admin_ep_message", None)
    if mensagem:
        st.success(mensagem)
    visao, cadastro, edicao, historico = st.tabs(["Visão geral", "Novo carregador", "Editar carregador", "Histórico de recargas"])
    with visao:
        a, b, c = st.columns(3)
        a.metric("Carregadores", len(postos))
        b.metric("Online", sum(p["status"] == "online" for p in postos))
        c.metric("Manutenção / falha", sum(p["status"] in {"manutencao", "falha"} for p in postos))
        busca = st.text_input("Buscar por código ou localização", key="admin_ep_search")
        encontrados = [p for p in postos if busca.casefold() in f"{p['codigo']} {p['localizacao'] or ''}".casefold()]
        if encontrados:
            st.dataframe(pd.DataFrame([{
                "Código": p["codigo"], "Localização": p["localizacao"],
                "Potência (kW)": p["potencia_kw"], "Tarifa (R$/kWh)": p["tarifa_kwh"],
                "Status": ROTULOS.get(p["status"], p["status"]),
            } for p in encontrados]), hide_index=True, use_container_width=True)
        else:
            st.info("Nenhum carregador encontrado. Use a aba Novo carregador para cadastrar.")
    with cadastro:
        aba_cadastro(usuario["id"])
    with edicao:
        aba_edicao(usuario["id"], postos)
    with historico:
        aba_historico(usuario["id"], postos)
