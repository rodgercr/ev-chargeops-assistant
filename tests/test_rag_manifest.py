from pathlib import Path

import pytest

from preparar_rag import CAMINHO_MANIFESTO, carregar_documentos


def test_manifesto_carrega_documentos_versionados() -> None:
    documentos = carregar_documentos(CAMINHO_MANIFESTO)
    assert len(documentos) == 5
    assert {colecao for doc in documentos for colecao in doc.colecoes} == {
        "atendimento",
        "sindico",
    }
    assert len({doc.doc_id for doc in documentos}) == len(documentos)
    assert all(len(doc.sha256) == 64 for doc in documentos)


def test_manifesto_impede_arquivo_fora_da_base(tmp_path: Path) -> None:
    pasta = tmp_path / "knowledge_base"
    pasta.mkdir()
    (tmp_path / "fora.md").write_text("x" * 100, encoding="utf-8")
    manifesto = pasta / "manifest.json"
    manifesto.write_text(
        '{"documentos":[{"id":"x","arquivo":"../fora.md",'
        '"titulo":"X","colecoes":["atendimento"]}]}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="fora da knowledge_base"):
        carregar_documentos(manifesto)
