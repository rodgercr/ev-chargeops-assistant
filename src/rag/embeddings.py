"""Embeddings nomic locais; não mistura dimensões com MiniLM legado."""
import os
from functools import lru_cache
from langchain_ollama import OllamaEmbeddings
MODEL = "nomic-embed-text:latest"
@lru_cache(maxsize=1)
def modelo_embeddings():
    return OllamaEmbeddings(model=MODEL, base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                            client_kwargs={"timeout": 120})
def documentos(textos):
    return modelo_embeddings().embed_documents(["search_document: " + t for t in textos])
def pergunta(texto):
    return modelo_embeddings().embed_query("search_query: " + texto)
