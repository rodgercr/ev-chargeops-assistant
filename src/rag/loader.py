"""Carregamento validado da base expandida."""
from pathlib import Path
from preparar_rag import carregar_documentos as carregar_manifesto
ROOT = Path(__file__).resolve().parents[2]
MANIFESTO = ROOT / "data" / "knowledge_base" / "manifest.json"
def carregar_documentos():
    return carregar_manifesto(MANIFESTO)
