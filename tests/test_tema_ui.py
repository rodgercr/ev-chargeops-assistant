"""A troca de aparência não deve recriar a sessão nem apagar a conversa."""
from pathlib import Path
from streamlit.testing.v1 import AppTest
import pytest
from ui.tema import PALETAS

SCRIPT = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def luminancia(cor):
    canais = [int(cor[i:i+2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in canais]
    return sum(c * peso for c, peso in zip(linear, (.2126, .7152, .0722)))


@pytest.mark.parametrize("tema", ["claro", "escuro"])
def test_contraste_de_textos_e_botoes(tema):
    paleta = PALETAS[tema]
    pares = [(texto, fundo) for texto in ("text", "muted")
             for fundo in ("canvas", "panel", "panel-strong")]
    pares.append(("on-accent", "electric"))
    for texto, fundo in pares:
        a, b = sorted((luminancia(paleta[texto]), luminancia(paleta[fundo])))
        assert (b + .05) / (a + .05) >= 4.5, (tema, texto, fundo)


def test_painel_administrativo_nao_reintroduz_verde_fixo():
    fonte = (SCRIPT.parent / "ui" / "admin_carregadores.py").read_text(encoding="utf-8")
    assert "#0d1712" not in fonte
    assert "var(--panel" in fonte


def test_css_dos_controles_carregado_no_app():
    app = AppTest.from_file(str(SCRIPT)).run()
    estilos = "\n".join(m.value for m in app.markdown)
    assert ".st-key-theme_control button:hover" in estilos
    assert '.react-aria-ComboBox [role="group"]' in estilos
    assert 'filter: var(--native-table-filter)' in estilos
    assert '[data-testid="stTooltipContent"]' in estilos


def test_titulos_nao_usam_emojis_e_avatares_permanecem_visiveis():
    fonte = SCRIPT.read_text(encoding="utf-8")
    assert 'st.title("📊' not in fonte
    assert 'st.title("🔋' not in fonte
    assert 'st.title("🛠️' not in fonte
    assert 'ChatMessageAvatar"] svg' in fonte
    assert "visibility: visible !important" in fonte


def test_tema_claro_padrao_e_alternancia_no_login():
    app = AppTest.from_file(str(SCRIPT)).run()
    assert not app.exception
    assert app.session_state["tema_visual"] == "claro"
    assert app.button(key="alternar_tema").label == "Modo escuro"
    app.button(key="alternar_tema").click().run()
    assert not app.exception
    assert app.session_state["tema_visual"] == "escuro"
    assert app.button(key="alternar_tema").label == "Modo claro"
    app.button(key="alternar_tema").click().run()
    assert app.session_state["tema_visual"] == "claro"


def test_trocar_tema_preserva_conversa_e_usuario():
    app = AppTest.from_file(str(SCRIPT))
    usuario = {"id": "teste", "nome": "Teste", "username": "teste", "perfil": "morador"}
    mensagens = [{"role": "user", "content": "Olá"}]
    app.session_state["usuario"] = usuario
    app.session_state["mensagens"] = mensagens
    app.session_state["sessao_id"] = "sessao-teste"
    app.run()
    app.button(key="alternar_tema").click().run()
    assert not app.exception
    assert app.session_state["tema_visual"] == "escuro"
    assert app.session_state["usuario"] == usuario
    assert app.session_state["mensagens"] == mensagens
    assert app.session_state["sessao_id"] == "sessao-teste"
    cabecalho = "\n".join(m.value for m in app.markdown)
    assert "local-badge" not in cabecalho
    assert "IA local" not in cabecalho
