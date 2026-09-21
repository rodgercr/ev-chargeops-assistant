import pytest

from services.auth_service import validar_dados_cadastro


def test_cadastro_valido() -> None:
    erros = validar_dados_cadastro(
        "Maria Silva", "maria.silva", "maria@example.com", "Senha123", "Senha123"
    )
    assert erros == []


@pytest.mark.parametrize(
    ("nome", "usuario", "email", "senha", "confirmacao"),
    [
        ("M", "maria", "maria@example.com", "Senha123", "Senha123"),
        ("Maria", "m@", "maria@example.com", "Senha123", "Senha123"),
        ("Maria", "maria", "email-invalido", "Senha123", "Senha123"),
        ("Maria", "maria", "", "curta", "curta"),
        ("Maria", "maria", "", "Senha123", "Outra123"),
    ],
)
def test_cadastro_invalido(
    nome: str, usuario: str, email: str, senha: str, confirmacao: str
) -> None:
    assert validar_dados_cadastro(nome, usuario, email, senha, confirmacao)
