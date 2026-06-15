import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import os

load_dotenv()

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./data/chroma")

embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

def get_collection(nome: str):
    return client.get_or_create_collection(nome, embedding_function=embedding_fn)

def adicionar_documento(collection_nome: str, texto: str, doc_id: str, metadados: dict = {}):
    col = get_collection(collection_nome)
    try:
        col.delete(ids=[doc_id])
    except:
        pass
    col.add(documents=[texto], ids=[doc_id], metadatas=[metadados])

def buscar_contexto(collection_nome: str, pergunta: str, n: int = 3) -> tuple[str, list[str]]:
    col = get_collection(collection_nome)
    if col.count() == 0:
        return "", []
    resultados = col.query(
        query_texts=[pergunta],
        n_results=min(n, col.count())
    )
    docs = resultados["documents"][0]
    ids  = resultados["ids"][0]
    return "\n\n".join(docs), ids
