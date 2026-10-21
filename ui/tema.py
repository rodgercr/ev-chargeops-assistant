"""Tema visual por sessão, sem modificar configurações globais de outros usuários."""
import streamlit as st
from pathlib import Path


PALETAS = {
    "claro": {
        "canvas": "#ffffff", "panel": "#f7f7f8", "panel-strong": "#ededf0",
        "text": "#18181b", "muted": "#62626b", "line": "#dcdce1",
        "electric": "#27272a", "electric-soft": "#e8e8ed",
        "on-accent": "#ffffff", "shadow": "rgba(0,0,0,.06)",
        "logo-filter": "brightness(0)",
        "native-table-filter": "none",
    },
    "escuro": {
        "canvas": "#18181b", "panel": "#232326", "panel-strong": "#303035",
        "text": "#fafafa", "muted": "#b4b4be", "line": "#414147",
        "electric": "#f4f4f5", "electric-soft": "#36363c",
        "on-accent": "#18181b", "shadow": "rgba(0,0,0,.18)",
        "logo-filter": "brightness(0) invert(1)",
        "native-table-filter": "invert(1) grayscale(1) contrast(1.15)",
    },
}


def alternar_tema() -> None:
    st.session_state.tema_visual = (
        "escuro" if st.session_state.get("tema_visual", "claro") == "claro" else "claro"
    )


def aplicar_tema() -> None:
    tema = st.session_state.get("tema_visual", "claro")
    if tema not in PALETAS:
        tema = "claro"
    st.session_state.tema_visual = tema
    variaveis = ";".join(f"--{chave}:{valor}" for chave, valor in PALETAS[tema].items())
    esquema = "light" if tema == "claro" else "dark"
    st.markdown(
        f"<style>:root {{{variaveis};color-scheme:{esquema};}}"
        ".chat-logo {filter:var(--logo-filter);}</style>",
        unsafe_allow_html=True,
    )


def controle_tema(logo_data_uri: str) -> None:
    st.markdown(
        "<style>" + Path(__file__).with_name("tema_controles.css").read_text(encoding="utf-8") + "</style>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="site-header"><img class="chat-logo" src="{logo_data_uri}" alt="GoodWe AI"></div>',
        unsafe_allow_html=True,
    )
    escuro = st.session_state.tema_visual == "escuro"
    with st.container(key="theme_control"):
        st.button(
            "Modo claro" if escuro else "Modo escuro",
            icon=":material/light_mode:" if escuro else ":material/dark_mode:",
            key="alternar_tema", on_click=alternar_tema,
        )
