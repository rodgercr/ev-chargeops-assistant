"""Recuperação autorizada e rejeição conservadora de instruções em documentos."""
import re
from functools import lru_cache
from src.rag.loader import carregar_documentos
from src.rag.chunking import criar_trechos
from src.rag.vector_store import nome_indice, colecao
from src.rag.embeddings import pergunta as embed
PADRAO_INJECAO = re.compile(
    r"ignore.{0,50}(instru|regra|previous)|desconsidere.{0,50}(instru|regra)|"
    r"system\s*prompt|reveal.{0,30}(secret|password)|"
    r"<\s*/?\s*(system|assistant)\s*>|envie.{0,50}(senha|credencia)", re.I | re.S)
def documento_seguro(texto):
    return not bool(PADRAO_INJECAO.search(texto))
@lru_cache(maxsize=1)
def indice_atual():
    return colecao(nome_indice(criar_trechos(carregar_documentos())))
def recuperar(pergunta, perfil="morador", k=4, col=None):
    col = col if col is not None else indice_atual()
    if not col.count():
        raise RuntimeError("Índice Sprint 4 ausente. Execute preparar_rag_sprint4.cmd.")
    autorizadas = ["atendimento,sindico"] if perfil == "morador" else ["atendimento,sindico", "sindico"]
    resultado = col.query(query_embeddings=[embed(pergunta)], n_results=min(max(k*2, 8), col.count()),
                          where={"colecoes": {"$in": autorizadas}},
                          include=["documents", "metadatas", "distances"])
    itens = []
    for ident, texto, meta, distancia in zip(resultado["ids"][0], resultado["documents"][0],
                                            resultado["metadatas"][0], resultado["distances"][0]):
        if documento_seguro(texto):
            itens.append({"id": ident, "texto": texto, "metadados": meta, "distancia": distancia})
        if len(itens) == k:
            break
    return itens
def formatar_contexto(itens):
    return "\n\n".join(f"[Fonte: {r['metadados']['source_id']}] {r['metadados']['titulo']}\n{r['texto']}" for r in itens)
def buscar_contexto(colecao_nome, pergunta, n=4):
    itens = recuperar(pergunta, "morador" if colecao_nome == "atendimento" else "sindico", n)
    return formatar_contexto(itens), list(dict.fromkeys(r["metadados"]["source_id"] for r in itens))
