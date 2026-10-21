"""Recuperação compartilhada pelo chatbot e pelo benchmark, sem abrir bancos."""
from __future__ import annotations


def consultar_trechos(colecao, pergunta: str, n: int = 3) -> list[dict]:
    if n < 1:
        raise ValueError("n deve ser positivo")
    quantidade = colecao.count()
    if not quantidade:
        return []
    resultado = colecao.query(
        query_texts=[pergunta], n_results=min(n, quantidade),
        include=["documents", "metadatas", "distances"],
    )
    return [
        {"id": doc_id, "texto": texto, "metadados": meta or {}, "distancia": distancia}
        for doc_id, texto, meta, distancia in zip(
            resultado["ids"][0], resultado["documents"][0],
            resultado["metadatas"][0], resultado["distances"][0], strict=True,
        )
    ]


def formatar_contexto(trechos: list[dict]) -> str:
    return "\n\n".join(f"[Fonte: {item['id']}]\n{item['texto']}" for item in trechos)


def dividir_em_trechos(texto: str, tamanho: int = 400, sobreposicao: int = 80) -> list[str]:
    """Quebra recursiva por parágrafos/frases, em caracteres, não tokens."""
    if tamanho < 1 or not 0 <= sobreposicao < tamanho:
        raise ValueError("Use tamanho positivo e 0 <= sobreposicao < tamanho")
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    return RecursiveCharacterTextSplitter(
        chunk_size=tamanho, chunk_overlap=sobreposicao,
        separators=["\n\n", "\n", ". ", " ", ""],
    ).split_text(texto)
