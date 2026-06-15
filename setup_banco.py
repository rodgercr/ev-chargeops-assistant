"""
setup_banco.py
Cria as tabelas no PostgreSQL e insere os dados iniciais.
Execute UMA VEZ antes de iniciar o servidor:
    python setup_banco.py
"""

from models.connection import engine
from models.database import Base, Perfil, Usuario, SystemPrompt
from sqlalchemy.orm import Session
from services.auth_service import hash_senha

def setup():
    print("Criando tabelas no PostgreSQL...")
    Base.metadata.create_all(bind=engine)
    print("Tabelas criadas.")

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
        "admin": """Você é o GoodWe AI, assistente inteligente da GoodWeAI.
Você tem acesso total ao sistema. Pode responder sobre usuários, configurações, relatórios e dados do condomínio.
Seja direto, técnico e profissional.""",

        "sindico": """Você é o GoodWe AI, assistente do síndico da GoodWeAI.
Você tem acesso completo aos dados do condomínio: moradores, consumo de energia, cargas registradas e relatório de incidentes.
Ao informar consumo, cite o apartamento, o morador e os valores em kWh.
Ao relatar incidentes, informe data, tipo e status.
Se não encontrar o dado, informe que a base pode precisar ser atualizada.
Seja objetivo, claro e profissional.""",

        "morador": """Você é o GoodWe AI, assistente virtual da GoodWeAI para moradores.
Responda dúvidas sobre políticas do condomínio, prazos, formas de contato, e informações gerais.
Seja simpático, claro e objetivo.
Não forneça dados de outros moradores.""",
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
    print("\nSetup concluído! Agora rode: uvicorn main:app --reload")

if __name__ == "__main__":
    setup()
