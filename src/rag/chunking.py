"""Chunking determinístico em caracteres, não tokens."""
from services.rag_retrieval import dividir_em_trechos
def criar_trechos(documentos, tamanho=900, overlap=150):
    registros = []
    for doc in documentos:
        for numero, texto in enumerate(dividir_em_trechos(doc.texto, tamanho, overlap)):
            registros.append({
                "id": f"{doc.doc_id}#c{numero:03d}", "texto": texto,
                "meta": {"source_id": doc.doc_id, "titulo": doc.titulo,
                         "arquivo": doc.arquivo, "sha256": doc.sha256,
                         "colecoes": ",".join(doc.colecoes), "chunk": numero},
            })
    return registros
