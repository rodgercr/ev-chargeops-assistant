"""
setup_banco.py
Cria as tabelas no PostgreSQL e insere os dados iniciais.
Execute UMA VEZ antes de iniciar o servidor:
    python setup_banco.py
"""

from pathlib import Path

from models.connection import engine
from models.database import Base, Perfil, Usuario, SystemPrompt
from sqlalchemy import text
from sqlalchemy.orm import Session
from services.auth_service import hash_senha


RAIZ_PROJETO = Path(__file__).resolve().parent


def carregar_prompt(nome: str) -> str:
    return (RAIZ_PROJETO / "prompts" / f"{nome}.txt").read_text(
        encoding="utf-8"
    ).strip()


def garantir_schema_atual() -> None:
    """Atualiza bancos existentes sem apagar usuários ou históricos."""
    with engine.begin() as conexao:
        conexao.execute(
            text(
                """
                ALTER TABLE historico_conversas
                ADD COLUMN IF NOT EXISTS session_id VARCHAR(100)
                """
            )
        )
        conexao.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_historico_conversas_session_id
                ON historico_conversas (session_id)
                """
            )
        )
    print("Schema de memória por sessão verificado.")

def setup():
    print("Criando tabelas no PostgreSQL...")
    Base.metadata.create_all(bind=engine)
    garantir_schema_atual()
    print("Tabelas criadas ou atualizadas.")

    db = Session(bind=engine)

    # ── PERFIS ──
    perfis_dados = [
        ("admin",   "Administrador do sistema"),
        ("sindico", "Síndico do condomínio"),
        ("morador", "Morador do condomínio"),
    ]
    perfis = {}
    for nome, desc in perfis_dados:
        p = db.query(Perfil).filter(Perfil.nome == nome).first()
        if not p:
            p = Perfil(nome=nome, descricao=desc)
            db.add(p)
            db.flush()
            print(f"  Perfil criado: {nome}")
        perfis[nome] = p

    # ── USUÁRIOS INICIAIS ──
    usuarios_dados = [
        ("admin",   "admin123",   "Administrador",  "admin"),
        ("sindico", "sindico123", "Síndico",         "sindico"),
        ("morador", "morador123", "Morador Teste",   "morador"),
    ]
    for username, senha, nome, perfil_nome in usuarios_dados:
        if not db.query(Usuario).filter(Usuario.username == username).first():
            db.add(Usuario(
                username=username,
                senha_hash=hash_senha(senha),
                nome=nome,
                perfil_id=perfis[perfil_nome].id
            ))
            print(f"  Usuário criado: {username} / {senha}")

    # ── SYSTEM PROMPTS ──
    prompts_dados = {
        "admin": carregar_prompt("sindico"),
        "sindico": carregar_prompt("sindico"),
        "morador": carregar_prompt("morador"),
    }

    for perfil_nome, conteudo in prompts_dados.items():
        perfil = perfis[perfil_nome]
        existe = db.query(SystemPrompt).filter(
            SystemPrompt.perfil_id == perfil.id,
            SystemPrompt.ativo == True
        ).first()
        if not existe:
            db.add(SystemPrompt(
                perfil_id=perfil.id,
                conteudo=conteudo,
                versao=1,
                ativo=True
            ))
            print(f"  System prompt criado: {perfil_nome}")

    db.commit()
    db.close()
    print("\nSetup concluído! Agora rode executar.cmd.")

if __name__ == "__main__":
    setup()
