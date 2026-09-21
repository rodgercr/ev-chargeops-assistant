"""Reconstrói as coleções do RAG a partir da base versionada no repositório."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


RAIZ_PROJETO = Path(__file__).resolve().parent
PASTA_BASE = RAIZ_PROJETO / "knowledge_base"
CAMINHO_MANIFESTO = PASTA_BASE / "manifest.json"


@dataclass(frozen=True)
class DocumentoRAG:
    doc_id: str
    arquivo: str
    titulo: str
    colecoes: tuple[str, ...]
    texto: str
    sha256: str


def carregar_documentos(
    caminho_manifesto: Path = CAMINHO_MANIFESTO,
) -> list[DocumentoRAG]:
    """Valida o manifesto e carrega apenas arquivos dentro da knowledge_base."""
    caminho_manifesto = caminho_manifesto.resolve()
    pasta_base = caminho_manifesto.parent.resolve()
    manifesto = json.loads(caminho_manifesto.read_text(encoding="utf-8"))
    entradas = manifesto.get("documentos")
    if not isinstance(entradas, list) or not entradas:
        raise ValueError("O manifesto precisa conter uma lista não vazia de documentos.")

    documentos = []
    ids_vistos: set[str] = set()
    for entrada in entradas:
        doc_id = str(entrada.get("id", "")).strip()
        arquivo = str(entrada.get("arquivo", "")).strip()
        titulo = str(entrada.get("titulo", "")).strip()
        colecoes = tuple(
            str(colecao).strip() for colecao in entrada.get("colecoes", [])
        )
        if not doc_id or not arquivo or not titulo or not all(colecoes):
            raise ValueError(f"Entrada incompleta no manifesto: {entrada!r}")
        if doc_id in ids_vistos:
            raise ValueError(f"ID duplicado no manifesto: {doc_id}")

        caminho_documento = (pasta_base / arquivo).resolve()
        if pasta_base not in caminho_documento.parents:
            raise ValueError(f"Arquivo fora da knowledge_base: {arquivo}")
        if not caminho_documento.is_file():
            raise FileNotFoundError(f"Documento não encontrado: {arquivo}")

        texto = caminho_documento.read_text(encoding="utf-8").strip()
        if len(texto) < 80:
            raise ValueError(f"Documento muito curto ou vazio: {arquivo}")

        ids_vistos.add(doc_id)
        documentos.append(
            DocumentoRAG(
                doc_id=doc_id,
                arquivo=arquivo,
                titulo=titulo,
                colecoes=colecoes,
                texto=texto,
                sha256=hashlib.sha256(texto.encode("utf-8")).hexdigest(),
            )
        )
    return documentos


def preparar(documentos: list[DocumentoRAG]) -> None:
    from services.rag_service import (
        CHROMA_DB_PATH,
        EMBEDDING_MODEL,
        adicionar_documento,
        get_collection,
        remover_documentos_gerenciados,
    )

    colecoes = sorted(
        {colecao for documento in documentos for colecao in documento.colecoes}
    )
    for colecao in colecoes:
        removidos = remover_documentos_gerenciados(colecao)
        if removidos:
            print(f"[LIMPEZA] {colecao}: {removidos} documento(s) anterior(es).")

    for documento in documentos:
        metadados = {
            "origem": "base_reproduzivel",
            "arquivo": documento.arquivo,
            "titulo": documento.titulo,
            "sha256": documento.sha256,
        }
        for colecao in documento.colecoes:
            adicionar_documento(
                colecao,
                documento.texto,
                documento.doc_id,
                metadados,
            )
            print(f"[INDEXADO] {colecao}/{documento.doc_id}")

    print("\nRAG preparado com sucesso.")
    print(f"Modelo de embeddings: {EMBEDDING_MODEL}")
    print(f"ChromaDB: {CHROMA_DB_PATH.resolve()}")
    for colecao in colecoes:
        print(f"Coleção {colecao}: {get_collection(colecao).count()} documento(s).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepara o RAG reproduzível.")
    parser.add_argument(
        "--validar",
        action="store_true",
        help="Valida a base sem iniciar o modelo de embeddings.",
    )
    argumentos = parser.parse_args()
    documentos = carregar_documentos()
    print(f"Manifesto válido: {len(documentos)} documento(s).")
    if not argumentos.validar:
        preparar(documentos)


if __name__ == "__main__":
    main()
