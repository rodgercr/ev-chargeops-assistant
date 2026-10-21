"""Testes rápidos, sem baixar modelos e sem acessar PostgreSQL/Ollama."""
import copy
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from evals.rag_benchmark import METRICS, VARIANTS, digest, load_cases, summarize, report_markdown
from preparar_rag import carregar_documentos
from services.rag_retrieval import consultar_trechos, dividir_em_trechos, formatar_contexto

ROOT = Path(__file__).resolve().parents[1]


def test_dataset_has_sources_allowed_for_profile():
    cases = load_cases(ROOT / "evals/rag_dataset.json", carregar_documentos())
    assert len(cases) == 10
    assert sum(c["category"] == "dado_ausente" for c in cases) == 2


def test_dataset_rejects_private_source_for_morador(tmp_path):
    data = json.loads((ROOT / "evals/rag_dataset.json").read_text(encoding="utf-8"))
    data["cases"][0]["source_ids"] = ["operacao-sindico"]
    target = tmp_path / "dataset.json"
    target.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="incompatível"):
        load_cases(target, carregar_documentos())


def test_dataset_rejects_duplicate_ids(tmp_path):
    data = json.loads((ROOT / "evals/rag_dataset.json").read_text(encoding="utf-8"))
    data["cases"].append(data["cases"][0])
    target = tmp_path / "dataset.json"
    target.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicado"):
        load_cases(target, carregar_documentos())


def test_chunking_is_deterministic_and_bounded():
    text = "Primeira regra de recarga. " * 80
    chunks = dividir_em_trechos(text)
    assert len(chunks) > 1
    assert all(0 < len(chunk) <= 400 for chunk in chunks)
    assert chunks == dividir_em_trechos(text)
    assert dividir_em_trechos("") == []
    with pytest.raises(ValueError):
        dividir_em_trechos(text, 50, 50)


def test_empty_collection_does_not_query():
    collection = Mock()
    collection.count.return_value = 0
    assert consultar_trechos(collection, "recarga") == []
    collection.query.assert_not_called()
    assert formatar_contexto([]) == ""


def test_retrieval_preserves_rank_and_production_context():
    collection = Mock()
    collection.count.return_value = 2
    collection.query.return_value = {
        "ids": [["b", "a"]], "documents": [["Texto B", "Texto A"]],
        "metadatas": [[{"source_id": "b"}, None]], "distances": [[0.1, 0.2]],
    }
    chunks = consultar_trechos(collection, "pergunta")
    assert collection.query.call_args.kwargs["n_results"] == 2
    assert [chunk["id"] for chunk in chunks] == ["b", "a"]
    assert formatar_contexto(chunks) == "[Fonte: b]\nTexto B\n\n[Fonte: a]\nTexto A"
    with pytest.raises(ValueError):
        consultar_trechos(collection, "pergunta", 0)


def test_summary_never_turns_failures_into_zero_or_unpaired_gains():
    rows = [
        {"id": "1", "variant": VARIANTS[0], "scores": {"faithfulness": 0.5}},
        {"id": "1", "variant": VARIANTS[1], "scores": {"faithfulness": 1.0}},
        {"id": "2", "variant": VARIANTS[0], "scores": {"faithfulness": None}},
        {"id": "2", "variant": VARIANTS[1], "scores": {"faithfulness": 0.1}},
        {"id": "3", "variant": VARIANTS[0], "scores": {"faithfulness": float("nan")}},
    ]
    result = summarize(rows, 3)
    assert result[VARIANTS[0]]["faithfulness"] == {"mean": 0.5, "valid": 1, "expected": 3}
    assert result["paired"]["faithfulness"]["delta"] == 0.5
    assert result["paired"]["faithfulness"]["valid_pairs"] == 1
    assert result["paired"]["context_recall"]["delta"] is None


def test_fingerprint_changes_when_reference_or_configuration_changes():
    config = {"cases": [{"reference": "Valor ausente"}], "top_k": 3}
    assert digest(config) == digest(copy.deepcopy(config))
    changed = copy.deepcopy(config)
    changed["cases"][0]["reference"] = "Outra referência"
    assert digest(config) != digest(changed)


def test_empty_report_does_not_claim_complete():
    result = {"rows": [], "cases": [1], "started_at": "2026-09-28", "status": "parcial",
              "config": {"generator": "local", "judge": "local", "embedding": "local", "strictness": 3}}
    report = report_markdown(result)
    assert "**parcial**" in report
    assert "| N/D |" in report
    assert "0/1" in report
