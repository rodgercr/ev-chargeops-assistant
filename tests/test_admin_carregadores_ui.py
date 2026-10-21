"""Testes da página web Streamlit com banco isolado."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from test_admin_eletropostos import ambiente_admin, inserir_sessao
from services.admin_eletropostos import listar_eletropostos


def pagina_teste():
    from ui.admin_carregadores import tela_carregadores
    tela_carregadores()


def abrir_pagina(a, monkeypatch, perfil="admin", ator=None):
    import ui.admin_carregadores as ui
    monkeypatch.setattr(ui, "SessionLocal", a["factory"])
    app = AppTest.from_function(pagina_teste, default_timeout=15)
    app.session_state["usuario"] = {
        "id": str(ator or a["users"][perfil]), "perfil": perfil,
        "nome": "Usuário de teste", "username": "teste",
    }
    app.run()
    assert not app.exception
    return app


def botao(app, label):
    return next(b for b in app.button if b.label == label)


def campo(elementos, prefixo):
    return next(c for c in elementos if c.key.startswith(prefixo))


def test_pagina_admin_renderiza_as_quatro_abas(ambiente_admin, monkeypatch):
    app = abrir_pagina(ambiente_admin, monkeypatch)
    assert [tab.label for tab in app.tabs] == ["Visão geral", "Novo carregador", "Editar carregador", "Histórico de recargas"]
    assert any("Nenhuma recarga" in m.value for m in app.info)
    assert app.title[0].value == "Gerenciar carregadores"


@pytest.mark.parametrize("perfil,permitidos", [
    ("morador", {"Chat", "Meus dados"}),
    ("sindico", {"Chat", "Operação"}),
])
def test_botoes_do_menu_respeitam_o_perfil(ambiente_admin, perfil, permitidos):
    a = ambiente_admin
    script = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    app = AppTest.from_file(str(script), default_timeout=15)
    app.session_state["usuario"] = {"id": str(a["users"][perfil]), "perfil": perfil, "nome": "Teste", "username": "teste"}
    app.session_state["pagina_atual"] = "Administração"
    app.run()
    assert not app.exception
    destinos = {b.label for b in app.sidebar.button if b.key.startswith("nav_")}
    assert destinos == permitidos
    assert app.session_state["pagina_atual"] == "Chat"


def test_acoes_do_rodape_criam_conversa_e_encerram_sessao(ambiente_admin, monkeypatch):
    a = ambiente_admin
    import ui.admin_carregadores as ui
    monkeypatch.setattr(ui, "SessionLocal", a["factory"])
    script = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    app = AppTest.from_file(str(script), default_timeout=15)
    app.session_state["usuario"] = {"id": str(a["users"]["admin"]), "perfil": "admin", "nome": "Teste", "username": "teste"}
    app.session_state["pagina_atual"] = "Gerenciar carregadores"
    app.run()
    sessao_anterior = app.session_state["sessao_id"]
    botao(app, "Nova conversa").click().run()
    assert not app.exception
    assert app.session_state["pagina_atual"] == "Chat"
    assert app.session_state["sessao_id"] != sessao_anterior
    botao(app, "Sair").click().run()
    assert not app.exception
    assert app.session_state["usuario"] is None
    assert [t.label for t in app.tabs] == ["Entrar", "Criar conta"]


def test_cadastro_pela_interface(ambiente_admin, monkeypatch):
    a = ambiente_admin
    app = abrir_pagina(a, monkeypatch)
    app.text_input(key="admin_ep_create_0_codigo").set_value("ep-02")
    app.text_input(key="admin_ep_create_0_local").set_value("Garagem B")
    app.number_input(key="admin_ep_create_0_tarifa").set_value(0.0)
    botao(app, "Cadastrar carregador").click().run()
    assert not app.exception
    assert any("cadastrado" in s.value for s in app.success)
    with a["factory"]() as db:
        postos = listar_eletropostos(db, a["users"]["admin"])
    assert len(postos) == 2
    assert postos[1]["codigo"] == "EP-02" and postos[1]["tarifa_kwh"] == 0


def test_edicao_pela_interface_exige_confirmacao(ambiente_admin, monkeypatch):
    a = ambiente_admin
    app = abrir_pagina(a, monkeypatch)
    campo(app.number_input, f"admin_ep_edit_{a['posto']}_1_tarifa").set_value(0.0)
    campo(app.number_input, f"admin_ep_edit_{a['posto']}_1_potencia").set_value(50.0)
    botao(app, "Salvar alterações").click().run()
    assert not app.exception
    assert any("confirmação" in m.value for m in app.warning)
    with a["factory"]() as db:
        assert listar_eletropostos(db, a["users"]["admin"])[0]["tarifa_kwh"] == 1.2
    campo(app.checkbox, "admin_ep_confirm_").check()
    botao(app, "Salvar alterações").click().run()
    assert not app.exception
    assert any("atualizado" in s.value for s in app.success)
    with a["factory"]() as db:
        posto = listar_eletropostos(db, a["users"]["admin"])[0]
    assert posto["tarifa_kwh"] == 0 and posto["potencia_kw"] == 50


def test_historico_na_interface(ambiente_admin, monkeypatch):
    a = ambiente_admin
    inserir_sessao(a)
    a["db"].commit()
    app = abrir_pagina(a, monkeypatch)
    assert not app.exception
    assert any(m.label == "Recargas no filtro" and m.value == "1" for m in app.metric)
    assert any("Tarifa registrada (R$/kWh)" in frame.value.columns for frame in app.dataframe)


@pytest.mark.parametrize("perfil", ["morador", "sindico"])
def test_pagina_nao_renderiza_para_outros_perfis(ambiente_admin, monkeypatch, perfil):
    app = abrir_pagina(ambiente_admin, monkeypatch, perfil)
    assert not app.tabs and not app.text_input
    assert any("exclusiva" in m.value for m in app.error)


def test_perfil_falso_em_session_state_nao_concede_acesso(ambiente_admin, monkeypatch):
    a = ambiente_admin
    app = abrir_pagina(a, monkeypatch, perfil="admin", ator=a["users"]["morador"])
    assert not app.tabs
    assert any("restrito" in m.value for m in app.warning)


def test_navegacao_principal_oferece_a_pagina_para_admin(ambiente_admin, monkeypatch):
    a = ambiente_admin
    import ui.admin_carregadores as ui
    monkeypatch.setattr(ui, "SessionLocal", a["factory"])
    script = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    app = AppTest.from_file(str(script), default_timeout=15)
    app.session_state["usuario"] = {"id": str(a["users"]["admin"]), "perfil": "admin", "nome": "Admin teste", "username": "teste"}
    app.run()
    assert not app.exception
    assert any(b.label == "Gerenciar carregadores" for b in app.sidebar.button)
    botao(app, "Gerenciar carregadores").click().run()
    assert not app.exception
    assert app.title[0].value == "Gerenciar carregadores"
