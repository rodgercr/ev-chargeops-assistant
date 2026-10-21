"""Interface Streamlit do GoodWeAI — EV ChargeOps Assistant."""

from __future__ import annotations

import json
import base64
import uuid
from contextlib import contextmanager
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st
from ui.tema import aplicar_tema, controle_tema
from sqlalchemy import desc, func

from models.connection import SessionLocal
from models.database import HistoricoConversa, SystemPrompt, Usuario
from models.ev_models import (
    Eletroposto,
    GeracaoSolar,
    Incidente,
    SessaoCarregamento,
)
from services.auth_service import (
    autenticar_usuario,
    criar_conta_morador,
    get_system_prompt,
    validar_dados_cadastro,
)


RAIZ_PROJETO = Path(__file__).resolve().parent
CAMINHO_LOGO = RAIZ_PROJETO / "assets" / "goodweai-logo.png"
CAMINHO_ICONE = RAIZ_PROJETO / "assets" / "goodweai.ico"
LOGO_DATA_URI = (
    "data:image/png;base64,"
    + base64.b64encode(CAMINHO_LOGO.read_bytes()).decode("ascii")
)


st.set_page_config(
    page_title="GoodWe AI",
    page_icon=str(CAMINHO_ICONE),
    layout="wide",
    initial_sidebar_state="expanded" if st.session_state.get("usuario") else "collapsed",
)


aplicar_tema()

st.markdown(
    """
    <style>

        html, body, [class*="css"] { font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
        #MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }
        /* O controle da versão instalada fica no header, não no sidebar. */
        header[data-testid="stHeader"] { z-index: 1201 !important; }
        [data-testid="stExpandSidebarButton"] {
            visibility: visible !important;
            position: fixed;
            top: .8rem;
            left: .75rem;
            z-index: 1202;
            color: var(--text) !important;
            background: var(--panel) !important;
            border: 1px solid var(--line) !important;
            border-radius: 8px;
            pointer-events: auto;
        }
        [data-testid="stSidebar"] { z-index: 1203 !important; }
        [data-testid="stSidebarCollapseButton"] { visibility: visible !important; }
        [data-testid="stHeadingLink"],
        a[aria-label="Link to heading"] { display: none !important; }
        .stApp {
            color: var(--text);
            background-color: var(--canvas);
            background-image: none;
        }
        .main .block-container {
            max-width: 1040px;
            padding-top: 1.1rem;
            padding-bottom: 7rem;
        }
        [data-testid="stSidebar"], [data-testid="stSidebarContent"] {
            background: var(--panel) !important;
            color: var(--text);
            border-right: 1px solid var(--line);
        }
        [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            padding-top: .4rem;
            height: 100dvh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        [data-testid="stSidebarHeader"] { flex: 0 0 auto; }
        [data-testid="stSidebarUserContent"] {
            flex: 1 1 0;
            min-height: 0;
            display: flex;
            flex-direction: column;
            padding-bottom: max(1rem, env(safe-area-inset-bottom));
        }
        [data-testid="stSidebarUserContent"] > div {
            display: flex;
            flex: 1 1 0;
            min-height: 0;
            width: 100%;
        }
        [data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"] {
            flex: 1 1 0;
            min-height: 0;
            gap: 0;
        }
        [data-testid="stSidebar"] [data-testid="stLayoutWrapper"]:has(> .st-key-sidebar_main) {
            display: flex;
            flex: 1 1 0 !important;
            min-height: 0;
        }
        [data-testid="stSidebar"] [data-testid="stLayoutWrapper"]:has(> .st-key-sidebar_footer) {
            flex: 0 0 auto !important;
            margin-top: auto;
        }
        [data-testid="stSidebar"] .st-key-sidebar_main {
            flex: 1 1 0 !important;
            min-height: 0;
            overflow-y: auto;
            overflow-x: hidden;
            padding-bottom: 1rem;
        }
        [data-testid="stSidebar"] .st-key-sidebar_footer {
            flex: 0 0 auto !important;
            margin-top: auto;
            padding-top: 1rem;
            border-top: 1px solid var(--line);
            background: var(--panel);
            gap: .55rem;
        }
        [data-testid="stSidebar"] .stButton > button {
            width: 100%;
            min-height: 46px;
            justify-content: flex-start;
            gap: .65rem;
            padding: .7rem .95rem;
            border-radius: 14px !important;
            border: 1px solid transparent !important;
            background: transparent !important;
            color: var(--muted) !important;
            box-shadow: none !important;
            transition: background .15s ease, border-color .15s ease, color .15s ease;
        }
        [data-testid="stSidebar"] .stButton > button p { font-weight: 550; }
        [data-testid="stSidebar"] .stButton > button:hover {
            background: var(--panel-strong) !important;
            border-color: var(--line) !important;
            color: var(--text) !important;
        }
        [data-testid="stSidebar"] .stButton > button:focus-visible {
            outline: 2px solid var(--text) !important;
            outline-offset: 2px;
        }
        [data-testid="stSidebar"] .st-key-sidebar_nav [data-testid="stBaseButton-primary"] {
            background: var(--electric-soft) !important;
            border-color: var(--electric-soft) !important;
            color: var(--text) !important;
        }
        [data-testid="stSidebar"] .st-key-sidebar_footer .stButton > button {
            background: var(--panel-strong) !important;
            border-color: var(--line) !important;
        }
        .sidebar-user {
            margin: .65rem 0 1.1rem;
            padding: .9rem;
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 14px;
        }
        .sidebar-user strong { display: block; color: var(--text); overflow-wrap: anywhere; }
        .sidebar-user span { font-size: .8rem; color: var(--muted); }
        .sidebar-section-label {
            color: var(--muted);
            font-size: .68rem;
            letter-spacing: .13em;
            text-transform: uppercase;
            margin-bottom: .25rem;
        }

        .goodwe-brand {
            font-size: 1.55rem;
            font-weight: 850;
            letter-spacing: -.04em;
            color: var(--text);
        }
        .goodwe-brand span { color: var(--electric); }
        .goodwe-subtitle { color: var(--muted); margin: .2rem 0 1.5rem; }
        .stApp:has(.login-page-marker) [data-testid="stForm"] {
            padding: 1.15rem;
            background: var(--panel) !important;
            border: 1px solid var(--line);
            border-radius: 16px;
            box-shadow: 0 18px 48px var(--shadow);
        }
        [data-testid="InputInstructions"] { display: none !important; }

        .chat-topbar {
            position: fixed;
            z-index: 999;
            top: 0;
            right: 0;
            left: 0;
            height: 70px;
            padding: 0 1.25rem;
            padding-left: 4rem;
            padding-right: 11rem;
            background: var(--canvas);
            border-bottom: 1px solid var(--line);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
        }
        .chat-topbar-inner {
            width: min(780px, 100%);
            height: 100%;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .chat-topbar-spacer { height: 72px; }
        .stApp:has(.chat-page-marker) [data-testid="stMainBlockContainer"] {
            width: min(812px, 100%);
            max-width: 812px;
            margin-right: auto;
            margin-left: auto;
            padding-right: 1rem;
            padding-left: 1rem;
            box-sizing: border-box;
        }
        .chat-identity { display: flex; align-items: center; gap: .75rem; }
        .chat-logo-frame {
            width: 38px;
            height: 38px;
            flex: 0 0 38px;
            overflow: hidden;
            border-radius: 10px;
            background: transparent;
            box-shadow: none;
        }
        .chat-logo {
            display: block;
            width: 38px !important;
            height: 38px !important;
            max-width: 38px !important;
            object-fit: contain;
        }
        .chat-name { font-weight: 760; line-height: 1.1; }
        .chat-meta { color: var(--muted); font-size: .78rem; margin-top: .22rem; }
        .chat-hero { text-align: center; padding: 3.2rem 1rem 1.35rem; }
        .chat-hero h1 {
            margin: 0;
            color: var(--text);
            font-size: clamp(1.65rem, 4vw, 2.4rem);
            letter-spacing: -.045em;
        }
        .chat-hero p {
            max-width: 620px;
            margin: .8rem auto 0;
            color: var(--muted);
            font-size: .95rem;
            line-height: 1.65;
        }
        .status-card {
            border: 1px solid var(--line);
            background: var(--panel);
            padding: 1rem 1.2rem;
            border-radius: 16px;
        }
        .stButton > button, .stFormSubmitButton > button {
            min-height: 42px;
            color: var(--text);
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 13px;
            transition: border-color .18s ease, background .18s ease, transform .18s ease;
        }
        .stButton > button:hover, .stFormSubmitButton > button:hover {
            color: var(--text);
            background: var(--panel-strong);
            border-color: var(--electric-soft);
            transform: translateY(-1px);
        }
        .stButton > button:focus,
        .stButton > button:focus-visible,
        .stButton > button:active,
        .stFormSubmitButton > button:focus,
        .stFormSubmitButton > button:focus-visible,
        .stFormSubmitButton > button:active {
            border-color: var(--line) !important;
            outline: none !important;
            box-shadow: none !important;
        }
        .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
            color: var(--on-accent);
            font-weight: 750;
            background: var(--electric);
            border-color: var(--electric);
        }
        div[data-testid="column"] .stButton > button {
            min-height: 82px;
            justify-content: flex-start;
            padding: 1rem;
            text-align: left;
            font-weight: 650;
        }
        div[data-testid="stMetric"] {
            background: var(--panel);
            border: 1px solid var(--line);
            padding: 1rem;
            border-radius: 16px;
        }
        div[data-testid="stChatMessage"] {
            display: flex;
            justify-content: flex-start !important;
            gap: .65rem;
            margin-bottom: .45rem;
            padding: .5rem 0;
            background: transparent;
            border: 0;
            border-radius: 0;
        }
        div[data-testid="stChatMessage"] [data-testid*="ChatMessageAvatar"],
        div[data-testid="stChatMessage"] [data-testid^="chatAvatarIcon-"] {
            width: 28px;
            height: 28px;
            min-width: 28px;
            color: var(--muted) !important;
            background: transparent !important;
            border: 1px solid var(--line);
            box-shadow: none !important;
        }
        div[data-testid="stChatMessage"] [data-testid*="ChatMessageAvatar"] svg,
        div[data-testid="stChatMessage"] [data-testid*="ChatMessageAvatar"] path,
        div[data-testid="stChatMessage"] [data-testid*="ChatMessageAvatar"] span,
        div[data-testid="stChatMessage"] [data-testid^="chatAvatarIcon-"] svg,
        div[data-testid="stChatMessage"] [data-testid^="chatAvatarIcon-"] path,
        div[data-testid="stChatMessage"] [data-testid^="chatAvatarIcon-"] span {
            display: block !important;
            color: var(--text) !important;
            fill: currentColor !important;
            opacity: 1 !important;
            visibility: visible !important;
        }
        div[data-testid="stChatMessage"] [data-testid="stChatMessageContent"] {
            flex: 0 1 auto;
            width: auto;
            max-width: min(78%, 620px);
            padding: .62rem .82rem;
            color: var(--text);
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 4px 16px 16px 16px;
            margin: 0 !important;
        }
        .chat-role-marker { display: none; }
        div[data-testid="stElementContainer"]:has(.chat-role-marker),
        div[data-testid="stMarkdown"]:has(.chat-role-marker) {
            display: none !important;
            width: 0 !important;
            height: 0 !important;
            min-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        div[data-testid="stChatMessage"]:has(.chat-role-user) {
            flex-direction: row-reverse;
            justify-content: flex-start !important;
        }
        div[data-testid="stChatMessage"]:has(.chat-role-user)
        [data-testid="stChatMessageContent"] {
            background: var(--electric-soft);
            border-color: var(--electric-soft);
            border-radius: 16px 4px 16px 16px;
        }
        [data-testid="stChatInput"] {
            background: var(--panel);
            border: 1px solid var(--line) !important;
            border-radius: 18px;
            box-shadow: 0 16px 50px var(--shadow);
            outline: none !important;
        }
        [data-testid="stChatInput"]:focus,
        [data-testid="stChatInput"]:focus-within,
        [data-testid="stChatInput"] > div:focus,
        [data-testid="stChatInput"] > div:focus-within {
            border-color: var(--line) !important;
            outline: none !important;
            box-shadow: none !important;
        }
        [data-testid="stBottomBlockContainer"] {
            background: var(--canvas) !important;
            border-top: 1px solid var(--line);
        }
        .stApp:has(.chat-page-marker) [data-testid="stBottomBlockContainer"] > div {
            width: min(780px, calc(100% - 2rem));
            max-width: 780px;
            margin-right: auto;
            margin-left: auto;
        }
        [data-testid="stChatInput"] > div {
            background: var(--panel) !important;
            border: 0 !important;
            border-radius: 17px;
            outline: none !important;
            box-shadow: none !important;
        }
        [data-testid="stChatInput"] > div > div,
        [data-testid="stChatInputTextArea"] { background: transparent !important; }
        [data-testid="stChatInput"] textarea { color: var(--text); }
        [data-testid="stChatInput"] textarea::placeholder { color: var(--muted); }
        [data-testid="stChatInputSubmitButton"] { color: var(--electric); }
        [data-testid="stChatInputSubmitButton"]:not(:disabled),
        [data-testid="stChatInputSubmitButton"]:not(:disabled) * {
            color: var(--on-accent) !important;
        }
        [data-testid="stChatInputSubmitButton"]:hover,
        [data-testid="stChatInputSubmitButton"]:focus,
        [data-testid="stChatInputSubmitButton"]:active {
            color: var(--electric) !important;
            background: var(--electric-soft) !important;
            border-color: var(--electric-soft) !important;
            outline: none !important;
            box-shadow: none !important;
        }
        [data-baseweb="input"] > div, [data-baseweb="base-input"], [data-baseweb="textarea"] {
            background: var(--panel) !important;
            border-color: var(--line) !important;
        }
        .stTextInput input { background: var(--panel) !important; color: var(--text) !important; }
        [data-baseweb="tab-list"] { gap: .35rem; }
        [data-baseweb="tab"] { border-radius: 10px 10px 0 0; }
        [data-baseweb="tab-highlight"] { background-color: var(--text) !important; }
        button[role="tab"][aria-selected="true"],
        [data-testid="stTab"][aria-selected="true"],
        [data-testid="stTab"][aria-selected="true"] p {
            color: var(--text) !important;
        }
        [data-testid="stTab"][aria-selected="true"] .react-aria-SelectionIndicator {
            background: var(--text) !important;
        }
        [data-testid="stTab"]:hover,
        [data-testid="stTab"][data-hovered="true"],
        [data-testid="stTab"]:hover p,
        [data-testid="stTab"][data-hovered="true"] p {
            color: var(--text) !important;
        }
        .stApp:has(.login-page-marker) [data-testid="stTextInputRootElement"] {
            background: var(--panel) !important;
            border: 1px solid var(--line) !important;
            border-radius: 8px;
            box-shadow: none !important;
        }
        .stApp:has(.login-page-marker) [data-baseweb="input"]:focus-within,
        .stApp:has(.login-page-marker) [data-baseweb="base-input"]:focus-within,
        .stApp:has(.login-page-marker) [data-testid="stTextInputRootElement"]:focus-within {
            border: 1px solid var(--text) !important;
            outline: none !important;
            box-shadow: 0 0 0 1px var(--text) !important;
        }
        hr { border-color: var(--line) !important; }
        .stAlert { border-radius: 14px; }
        @media (max-width: 700px) {
            .main .block-container { padding-left: 1rem; padding-right: 1rem; }
            .chat-topbar { height: 62px; padding: 0 10rem 0 4rem; }
            .chat-topbar-spacer { height: 64px; }
            .chat-hero { padding-top: 2rem; }
        }
        [data-testid="stAppViewContainer"], [data-testid="stMain"] {
            background: var(--canvas); color: var(--text);
        }
        .stApp h1, .stApp h2, .stApp h3, .stApp label,
        [data-testid="stMarkdownContainer"], [data-testid="stMetricValue"],
        [data-testid="stMetricLabel"], [data-testid="stWidgetLabel"],
        [data-testid="stExpander"] summary { color: var(--text); }
        [data-testid="stCaptionContainer"] { color: var(--muted); }
        [data-baseweb="select"] > div, [data-testid="stNumberInputContainer"],
        [data-testid="stTextInputRootElement"], [data-testid="stDateInput"] input,
        [data-testid="stNumberInput"] input, [data-testid="stTextArea"] textarea,
        [data-baseweb="popover"], [role="listbox"] {
            background: var(--panel) !important; color: var(--text) !important;
            border-color: var(--line) !important;
        }
        [role="option"], [data-baseweb="select"] span { color: var(--text) !important; }
        [role="option"] { background: var(--panel) !important; }
        [role="option"]:hover { background: var(--panel-strong) !important; }
        [role="tooltip"] {
            background: var(--panel-strong) !important;
            color: var(--text) !important;
            border: 1px solid var(--line);
        }
        [data-testid="stNumberInput"] button, [data-testid="stTextInput"] button {
            color: var(--text) !important; background: var(--panel-strong) !important;
        }
        [data-testid="stChatInputSubmitButton"]:not(:disabled),
        [data-testid="stChatInputSubmitButton"]:not(:disabled):hover {
            background: var(--electric) !important; color: var(--on-accent) !important;
        }
        [data-testid="stChatInputSubmitButton"]:not(:disabled) svg {
            fill: currentColor !important;
        }
        [data-testid="stChatInputSubmitButton"]:disabled {
            background: var(--panel-strong) !important; color: var(--muted) !important;
        }
        [data-testid="stTab"] { color: var(--muted); }
        .stButton > button:focus-visible, .stFormSubmitButton > button:focus-visible {
            outline: 2px solid var(--text) !important; outline-offset: 2px;
        }
        .site-header {
            position: fixed; top: 0; left: 0; right: 0; height: 70px;
            background: var(--canvas); border-bottom: 1px solid var(--line);
            z-index: 998; display: flex; align-items: center; padding-left: 4rem;
            color: var(--text); font-weight: 750;
        }
        .st-key-theme_control {
            position: fixed; top: .8rem; right: 1rem;
            width: 140px !important; z-index: 1202;
        }
        .st-key-theme_control button { min-height: 40px; width: 100%; }
        [data-testid="stMainBlockContainer"] { padding-top: 5.5rem; }
        .stApp:has(.chat-page-marker) [data-testid="stMainBlockContainer"] { padding-top: 1rem; }
        .chat-meta { overflow-wrap: anywhere; }
        @media (max-width: 700px) {
            .site-header { height: 62px; }
            .chat-logo-frame { display: none; }
            .chat-meta { font-size: .65rem; }
            .st-key-theme_control { right: .5rem; width: 128px !important; }
        }

    </style>
    """,
    unsafe_allow_html=True,
)


@contextmanager
def abrir_banco():
    banco = SessionLocal()
    try:
        yield banco
    finally:
        banco.close()


def iniciar_estado() -> None:
    valores = {
        "usuario": None,
        "mensagens": [],
        "sessao_id": str(uuid.uuid4()),
        "pagina_atual": "Chat",
    }
    for chave, valor in valores.items():
        if chave not in st.session_state:
            st.session_state[chave] = valor


def sair() -> None:
    for chave in list(st.session_state):
        if chave.startswith("admin_ep_"):
            del st.session_state[chave]
    st.session_state.usuario = None
    st.session_state.pagina_atual = "Chat"
    st.session_state.mensagens = []
    st.session_state.sessao_id = str(uuid.uuid4())
    st.rerun()


def nova_conversa() -> None:
    st.session_state.pagina_atual = "Chat"
    st.session_state.mensagens = []
    st.session_state.sessao_id = str(uuid.uuid4())
    st.rerun()


def tela_login() -> None:
    esquerda, centro, direita = st.columns([1, 1.25, 1])
    with centro:
        st.markdown('<div class="login-page-marker"></div>', unsafe_allow_html=True)
        st.markdown('<div class="goodwe-brand">GOODWE<span>AI</span></div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="goodwe-subtitle">EV ChargeOps Assistant · FIAP × GoodWe</div>',
            unsafe_allow_html=True,
        )
        aba_entrar, aba_cadastrar = st.tabs(["Entrar", "Criar conta"])

        with aba_entrar:
            with st.form("login"):
                username = st.text_input("Usuário", key="login_usuario")
                password = st.text_input("Senha", type="password", key="login_senha")
                entrar = st.form_submit_button("Entrar", use_container_width=True)

            if entrar:
                if not username.strip() or not password:
                    st.warning("Preencha usuário e senha.")
                else:
                    try:
                        with abrir_banco() as banco:
                            usuario = autenticar_usuario(
                                banco, username.strip(), password
                            )
                            if not usuario:
                                st.error("Usuário ou senha incorretos.")
                            else:
                                st.session_state.usuario = {
                                    "id": str(usuario.id),
                                    "username": usuario.username,
                                    "nome": usuario.nome or usuario.username,
                                    "perfil": usuario.perfil.nome,
                                }
                                st.rerun()
                    except Exception as erro:
                        st.error("Não foi possível conectar ao banco de dados.")
                        st.caption(f"Detalhe técnico: {erro}")

        with aba_cadastrar:
            st.caption(
                "O cadastro público cria uma conta de morador. "
                "Perfis administrativos são criados somente pelo administrador."
            )
            with st.form("cadastro", clear_on_submit=True):
                nome_cadastro = st.text_input("Nome completo")
                usuario_cadastro = st.text_input("Nome de usuário")
                email_cadastro = st.text_input("E-mail (opcional)")
                senha_cadastro = st.text_input("Senha", type="password")
                confirmar_senha = st.text_input("Confirmar senha", type="password")
                cadastrar = st.form_submit_button(
                    "Criar conta", use_container_width=True
                )

            if cadastrar:
                erros = validar_dados_cadastro(
                    nome_cadastro,
                    usuario_cadastro,
                    email_cadastro,
                    senha_cadastro,
                    confirmar_senha,
                )
                if erros:
                    for erro in erros:
                        st.warning(erro)
                else:
                    try:
                        with abrir_banco() as banco:
                            criar_conta_morador(
                                banco,
                                nome=nome_cadastro,
                                username=usuario_cadastro,
                                email=email_cadastro,
                                password=senha_cadastro,
                            )
                        st.success("Conta criada! Use a aba Entrar para acessar.")
                    except ValueError as erro:
                        st.warning(str(erro))
                    except Exception as erro:
                        st.error("Não foi possível criar a conta.")
                        st.caption(f"Detalhe técnico: {erro}")


def pares_do_historico_atual() -> list[tuple[str, str]]:
    pares: list[tuple[str, str]] = []
    pergunta: str | None = None
    for mensagem in st.session_state.mensagens:
        if mensagem["role"] == "user":
            pergunta = mensagem["content"]
        elif mensagem["role"] == "assistant" and pergunta is not None:
            pares.append((pergunta, mensagem["content"]))
            pergunta = None
    return pares[-5:]


def salvar_historico(banco, pergunta: str, resposta: str, fontes: list[str]) -> None:
    banco.add(
        HistoricoConversa(
            usuario_id=st.session_state.usuario["id"],
            session_id=st.session_state.sessao_id,
            pergunta=pergunta,
            resposta=resposta,
            fontes=json.dumps(fontes, ensure_ascii=False),
        )
    )
    banco.commit()


def tela_chat() -> None:
    usuario = st.session_state.usuario
    nome = escape(usuario["nome"])
    perfil = escape(usuario["perfil"].capitalize())
    st.markdown(
        f"""
        <div class="chat-page-marker"></div>
        <div class="chat-topbar">
            <div class="chat-topbar-inner">
                <div class="chat-identity">
                    <div class="chat-logo-frame">
                        <img class="chat-logo" src="{LOGO_DATA_URI}" alt="Logo GoodWeAI">
                    </div>
                    <div>
                        <div class="chat-name">GoodWeAI</div>
                        <div class="chat-meta">{nome} · Perfil: {perfil}</div>
                    </div>
                </div>
            </div>
        </div>
        <div class="chat-topbar-spacer"></div>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.mensagens:
        st.markdown(
            """
            <div class="chat-hero">
                <h1>Energia inteligente, conversa simples.</h1>
                <p>
                    Consulte recargas, consumo, eletropostos e políticas do condomínio.
                    As respostas combinam dados locais, memória da sessão e a base RAG.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    for mensagem in st.session_state.mensagens:
        avatar = ":material/person:" if mensagem["role"] == "user" else ":material/bolt:"
        with st.chat_message(mensagem["role"], avatar=avatar):
            st.markdown(
                f'<span class="chat-role-marker chat-role-{mensagem["role"]}"></span>',
                unsafe_allow_html=True,
            )
            st.markdown(mensagem["content"])
            if mensagem.get("fontes"):
                with st.expander("Fontes consultadas"):
                    st.write(", ".join(mensagem["fontes"]))

    pergunta = st.chat_input("Pergunte sobre recargas, consumo ou eletropostos...")
    if not pergunta:
        return

    historico = pares_do_historico_atual()
    st.session_state.mensagens.append({"role": "user", "content": pergunta})
    with st.chat_message("user", avatar=":material/person:"):
        st.markdown(
            '<span class="chat-role-marker chat-role-user"></span>',
            unsafe_allow_html=True,
        )
        st.markdown(pergunta)

    with st.chat_message("assistant", avatar=":material/bolt:"):
        st.markdown(
            '<span class="chat-role-marker chat-role-assistant"></span>',
            unsafe_allow_html=True,
        )
        with st.spinner("Consultando dados e preparando a resposta..."):
            try:
                # Carregamento tardio: o modelo de embeddings só é iniciado
                # quando o usuário realmente envia uma pergunta.
                from services.llm_service import gerar_resposta

                with abrir_banco() as banco:
                    system_prompt = get_system_prompt(banco, usuario["perfil"])
                    resultado = gerar_resposta(
                        pergunta=pergunta,
                        system_prompt=system_prompt,
                        perfil=usuario["perfil"],
                        db=banco,
                        usuario_id=usuario["id"],
                        session_id=st.session_state.sessao_id,
                        historico=historico,
                    )
                    salvar_historico(
                        banco,
                        pergunta,
                        resultado["resposta"],
                        resultado.get("fontes", []),
                    )
                resposta = resultado["resposta"]
                fontes = resultado.get("fontes", [])
            except Exception as erro:
                resposta = "Não consegui concluir a consulta. Verifique o banco, o Ollama e tente novamente."
                fontes = []
                st.caption(f"Detalhe técnico: {erro}")

        st.markdown(resposta)
        if fontes:
            with st.expander("Fontes consultadas"):
                st.write(", ".join(fontes))

    st.session_state.mensagens.append(
        {"role": "assistant", "content": resposta, "fontes": fontes}
    )


def tabela(dados: list[dict], mensagem_vazia: str) -> None:
    if dados:
        st.dataframe(pd.DataFrame(dados), use_container_width=True, hide_index=True)
    else:
        st.info(mensagem_vazia)


def tela_operacional() -> None:
    st.title("Operação dos eletropostos")
    try:
        with abrir_banco() as banco:
            total_eps = banco.query(Eletroposto).count()
            online = banco.query(Eletroposto).filter(Eletroposto.status == "online").count()
            energia = banco.query(func.sum(SessaoCarregamento.energia_kwh)).scalar() or 0
            incidentes = banco.query(Incidente).filter(Incidente.status != "resolvido").count()

            eps = [
                {
                    "Código": ep.codigo,
                    "Localização": ep.localizacao,
                    "Potência (kW)": ep.potencia_kw,
                    "Tarifa (R$/kWh)": ep.tarifa_kwh,
                    "Status": ep.status,
                }
                for ep in banco.query(Eletroposto).order_by(Eletroposto.codigo).all()
            ]
            sessoes = [
                {
                    "Início": s.inicio,
                    "Usuário": s.usuario.username if s.usuario else "—",
                    "Eletroposto": s.eletroposto.codigo if s.eletroposto else "—",
                    "Energia (kWh)": s.energia_kwh,
                    "Custo (R$)": s.custo_total,
                    "Status": s.status,
                }
                for s in banco.query(SessaoCarregamento)
                .order_by(desc(SessaoCarregamento.inicio))
                .limit(30)
                .all()
            ]
            lista_incidentes = [
                {
                    "Data": i.criado_em,
                    "Eletroposto": i.eletroposto.codigo if i.eletroposto else "—",
                    "Tipo": i.tipo,
                    "Descrição": i.descricao,
                    "Status": i.status,
                }
                for i in banco.query(Incidente)
                .order_by(desc(Incidente.criado_em))
                .limit(30)
                .all()
            ]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Eletropostos", total_eps)
        col2.metric("Online", online)
        col3.metric("Energia registrada", f"{energia:.1f} kWh")
        col4.metric("Incidentes abertos", incidentes)

        aba_eps, aba_sessoes, aba_incidentes = st.tabs(
            ["Eletropostos", "Recargas recentes", "Incidentes"]
        )
        with aba_eps:
            tabela(eps, "Nenhum eletroposto cadastrado.")
        with aba_sessoes:
            tabela(sessoes, "Nenhuma recarga registrada.")
        with aba_incidentes:
            tabela(lista_incidentes, "Nenhum incidente registrado.")
    except Exception as erro:
        st.error("Não foi possível carregar o painel operacional.")
        st.caption(f"Detalhe técnico: {erro}")


def tela_meus_dados() -> None:
    usuario = st.session_state.usuario
    st.title("Minhas recargas")
    try:
        with abrir_banco() as banco:
            sessoes = [
                {
                    "Início": s.inicio,
                    "Eletroposto": s.eletroposto.codigo if s.eletroposto else "—",
                    "Energia (kWh)": s.energia_kwh,
                    "Duração (min)": s.duracao_minutos,
                    "Custo (R$)": s.custo_total,
                    "Status": s.status,
                }
                for s in banco.query(SessaoCarregamento)
                .filter(SessaoCarregamento.usuario_id == usuario["id"])
                .order_by(desc(SessaoCarregamento.inicio))
                .all()
            ]
            solar = [
                {
                    "Mês": g.mes_ano,
                    "Consumo (kWh)": g.consumo_kwh,
                    "Geração (kWh)": g.geracao_kwh,
                    "Saldo (kWh)": g.saldo_kwh,
                }
                for g in banco.query(GeracaoSolar)
                .filter(GeracaoSolar.usuario_id == usuario["id"])
                .all()
            ]
        aba_recargas, aba_solar = st.tabs(["Recargas", "Energia solar"])
        with aba_recargas:
            tabela(sessoes, "Você ainda não possui recargas registradas.")
        with aba_solar:
            tabela(solar, "Você ainda não possui registros de geração solar.")
    except Exception as erro:
        st.error("Não foi possível carregar seus dados.")
        st.caption(f"Detalhe técnico: {erro}")


def tela_administracao() -> None:
    st.title("Administração")
    try:
        with abrir_banco() as banco:
            usuarios = [
                {
                    "Usuário": u.username,
                    "Nome": u.nome,
                    "Perfil": u.perfil.nome if u.perfil else "—",
                    "Ativo": u.ativo,
                    "Criado em": u.criado_em,
                }
                for u in banco.query(Usuario).order_by(Usuario.username).all()
            ]
            prompts = [
                {
                    "Perfil": p.perfil.nome if p.perfil else "—",
                    "Versão": p.versao,
                    "Conteúdo": p.conteudo,
                }
                for p in banco.query(SystemPrompt)
                .filter(SystemPrompt.ativo.is_(True))
                .all()
            ]
            historico = [
                {
                    "Data": h.criado_em,
                    "Usuário": h.usuario.username if h.usuario else "—",
                    "Sessão": h.session_id[:8] if h.session_id else "legado",
                    "Pergunta": h.pergunta,
                    "Resposta": h.resposta,
                }
                for h in banco.query(HistoricoConversa)
                .order_by(desc(HistoricoConversa.criado_em))
                .limit(50)
                .all()
            ]

        aba_usuarios, aba_prompts, aba_historico = st.tabs(
            ["Usuários", "Prompts ativos", "Histórico"]
        )
        with aba_usuarios:
            tabela(usuarios, "Nenhum usuário cadastrado.")
        with aba_prompts:
            if not prompts:
                st.info("Nenhum prompt ativo.")
            for prompt in prompts:
                with st.expander(f"{prompt['Perfil']} · versão {prompt['Versão']}"):
                    st.code(prompt["Conteúdo"], language="text")
        with aba_historico:
            tabela(historico, "Nenhuma conversa registrada.")
    except Exception as erro:
        st.error("Não foi possível carregar a administração.")
        st.caption(f"Detalhe técnico: {erro}")


def selecionar_pagina(pagina: str) -> None:
    st.session_state.pagina_atual = pagina


def aplicativo() -> None:
    iniciar_estado()
    controle_tema(LOGO_DATA_URI)
    if not st.session_state.usuario:
        tela_login()
        return

    usuario = st.session_state.usuario
    paginas = {"Chat": ":material/chat_bubble_outline:"}
    if usuario["perfil"] in {"sindico", "admin"}:
        paginas["Operação"] = ":material/monitoring:"
    if usuario["perfil"] == "morador":
        paginas["Meus dados"] = ":material/battery_charging_full:"
    if usuario["perfil"] == "admin":
        paginas["Gerenciar carregadores"] = ":material/ev_station:"
        paginas["Administração"] = ":material/settings:"
    if st.session_state.pagina_atual not in paginas:
        st.session_state.pagina_atual = "Chat"

    with st.sidebar:
        with st.container(key="sidebar_main"):
            st.markdown('<div class="goodwe-brand">GOODWE<span>AI</span></div>', unsafe_allow_html=True)
            st.caption("EV ChargeOps Assistant")
            st.markdown(
                f'<div class="sidebar-user"><strong>{escape(usuario["nome"])}</strong>'
                f'<span>Perfil: {escape(usuario["perfil"].capitalize())}</span></div>',
                unsafe_allow_html=True,
            )
            st.markdown('<div class="sidebar-section-label">Navegação</div>', unsafe_allow_html=True)
            with st.container(key="sidebar_nav"):
                for nome, icone in paginas.items():
                    st.button(
                        nome, icon=icone, key=f"nav_{nome}", use_container_width=True,
                        type="primary" if st.session_state.pagina_atual == nome else "secondary",
                        on_click=selecionar_pagina, args=(nome,),
                    )
        with st.container(key="sidebar_footer"):
            if st.button("Nova conversa", icon=":material/add_comment:", key="sidebar_nova", use_container_width=True):
                nova_conversa()
            if st.button("Sair", icon=":material/logout:", key="sidebar_sair", use_container_width=True):
                sair()

    pagina = st.session_state.pagina_atual
    if pagina == "Chat":
        tela_chat()
    elif pagina == "Operação":
        tela_operacional()
    elif pagina == "Meus dados":
        tela_meus_dados()
    elif pagina == "Administração":
        tela_administracao()
    elif pagina == "Gerenciar carregadores":
        from ui.admin_carregadores import tela_carregadores
        tela_carregadores()


if __name__ == "__main__":
    aplicativo()
