"""Entrada Sprint 4: preserva interface e autenticação existentes."""
import runpy
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
runpy.run_path(str(ROOT / "streamlit_app.py"), run_name="__main__")
