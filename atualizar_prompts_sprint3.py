"""Publica os prompts atuais no PostgreSQL local como uma nova versão."""

from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.connection import engine
from models.database import Perfil, SystemPrompt


RAIZ_PROJETO = Path(__file__).resolve().parent


def carregar_prompt(nome: str) -> str:
    return (RAIZ_PROJETO / "prompts" / f"{nome}.txt").read_text(
        encoding="utf-8"
    ).strip()


def atualizar() -> None:
    prompts = {
        "admin": carregar_prompt("sindico"),
        "sindico": carregar_prompt("sindico"),
        "morador": carregar_prompt("morador"),
    }

    with Session(bind=engine) as db:
        for perfil_nome, conteudo in prompts.items():
            perfil = db.query(Perfil).filter(Perfil.nome == perfil_nome).first()
            if perfil is None:
                print(f"[IGNORADO] Perfil '{perfil_nome}' não encontrado.")
                continue

            ativo = (
                db.query(SystemPrompt)
                .filter(
                    SystemPrompt.perfil_id == perfil.id,
                    SystemPrompt.ativo.is_(True),
                )
                .order_by(SystemPrompt.versao.desc())
                .first()
            )
            if ativo and ativo.conteudo.strip() == conteudo:
                print(f"[OK] Prompt de {perfil_nome} já está atualizado.")
                continue

            ultima_versao = (
                db.query(func.max(SystemPrompt.versao))
                .filter(SystemPrompt.perfil_id == perfil.id)
                .scalar()
                or 0
            )
            db.query(SystemPrompt).filter(
                SystemPrompt.perfil_id == perfil.id,
                SystemPrompt.ativo.is_(True),
            ).update({"ativo": False}, synchronize_session=False)
            db.add(
                SystemPrompt(
                    perfil_id=perfil.id,
                    conteudo=conteudo,
                    versao=ultima_versao + 1,
                    ativo=True,
                )
            )
            print(
                f"[ATUALIZADO] {perfil_nome}: versão {ultima_versao + 1}."
            )

        db.commit()


if __name__ == "__main__":
    atualizar()
