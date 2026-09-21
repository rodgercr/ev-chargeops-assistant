"""Persistência e busca semântica do RAG local com ChromaDB."""

from __future__ import annotations

import os
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv


load_dotenv()

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
CHROMA_DB_PATH = Path(
    os.getenv("CHROMA_DB_PATH", str(RAIZ_PROJETO / "data" / "chroma"))
)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL
)
client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))


def get_collection(nome: str):
    return client.get_or_create_collection(
        nome,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )


def adicionar_documento(
    collection_nome: str,
    texto: str,
    doc_id: str,
    metadados: dict | None = None,
) -> None:
    """Inclui ou atualiza um documento usando um identificador determinístico."""
    get_collection(collection_nome).upsert(
        documents=[texto],
        ids=[doc_id],
        metadatas=[metadados or {}],
    )


def remover_documentos_gerenciados(collection_nome: str) -> int:
    """Remove somente documentos criados pelo preparador reproduzível."""
    colecao = get_collection(collection_nome)
    encontrados = colecao.get(where={"origem": "base_reproduzivel"})
    ids = encontrados.get("ids", [])
    if ids:
        colecao.delete(ids=ids)
    return len(ids)


def buscar_contexto(
    collection_nome: str, pergunta: str, n: int = 3
) -> tuple[str, list[str]]:
    colecao = get_collection(collection_nome)
    if colecao.count() == 0:
        return "", []

    resultados = colecao.query(
        query_texts=[pergunta],
        n_results=min(n, colecao.count()),
    )
    documentos = resultados.get("documents", [[]])[0]
    ids = resultados.get("ids", [[]])[0]
    trechos = [
        f"[Fonte: {doc_id}]\n{documento}"
        for doc_id, documento in zip(ids, documentos)
    ]
    return "\n\n".join(trechos), ids
