"""Reconstrói o índice nomic sem apagar índices antigos."""
import argparse
from src.rag.loader import carregar_documentos
from src.rag.chunking import criar_trechos
from src.rag.vector_store import nome_indice, indexar
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validar", action="store_true")
    args = parser.parse_args()
    docs = carregar_documentos()
    trechos = criar_trechos(docs)
    nome = nome_indice(trechos)
    print(f"Base: {len(docs)} documentos, {len(trechos)} trechos. Índice: {nome}")
    if not args.validar:
        print(f"Indexados: {indexar(trechos, nome).count()} trechos.")
if __name__ == "__main__":
    main()
