"""Índice persistente separado; preserva os índices antigos."""
import hashlib
import json
import os
from pathlib import Path
from functools import lru_cache
import chromadb
from chromadb.config import Settings
from src.rag.embeddings import documentos as embed, MODEL
ROOT = Path(__file__).resolve().parents[2]
@lru_cache(maxsize=1)
def cliente():
    return chromadb.PersistentClient(
        path=str(Path(os.getenv("SPRINT4_CHROMA_PATH", str(ROOT / "data" / "chroma_sprint4")))),
        settings=Settings(anonymized_telemetry=False))
def nome_indice(registros, tamanho=900, overlap=150):
    payload = {"modelo": MODEL, "size": tamanho, "overlap": overlap,
               "registros": [(r["id"], r["meta"]["sha256"]) for r in registros]}
    return "s4-" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:24]
def colecao(nome):
    return cliente().get_or_create_collection(nome, embedding_function=None, metadata={"hnsw:space": "cosine"})
def indexar(registros, nome):
    col = colecao(nome)
    existentes = set(col.get()["ids"])
    faltantes = [r for r in registros if r["id"] not in existentes]
    for inicio in range(0, len(faltantes), 16):
        lote = faltantes[inicio:inicio+16]
        col.upsert(ids=[r["id"] for r in lote], documents=[r["texto"] for r in lote],
                   embeddings=embed([r["texto"] for r in lote]), metadatas=[r["meta"] for r in lote])
    return col
