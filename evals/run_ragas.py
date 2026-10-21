"""Compara o RAG documental com RAGAS e Ollama, sem acessar dados de usuários."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Não transmitir conteúdo do benchmark por telemetria/tracing.
os.environ["RAGAS_DO_NOT_TRACK"] = "true"
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"

from evals.rag_benchmark import VARIANTS, METRICS, digest, load_cases, summarize, report_markdown
from preparar_rag import carregar_documentos
from services.rag_retrieval import consultar_trechos, dividir_em_trechos, formatar_contexto


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_result(path: Path, result: dict) -> None:
    result["updated_at"] = utc_now()
    result["summary"] = summarize(result["rows"], len(result["cases"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)
    path.with_suffix(".md").write_text(report_markdown(result), encoding="utf-8")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_indices(documents, embedding, fingerprint):
    import chromadb
    from chromadb.config import Settings

    client = chromadb.PersistentClient(
        path=str(ROOT / "data" / "ragas_chroma"),
        settings=Settings(anonymized_telemetry=False),
    )
    collections = {}
    for variant in VARIANTS:
        for name in ("atendimento", "sindico"):
            collection = client.get_or_create_collection(
                f"eval-{fingerprint[:16]}-{variant}-{name}", embedding_function=embedding,
                metadata={"hnsw:space": "cosine"},
            )
            records = []
            for doc in documents:
                if name not in doc.colecoes:
                    continue
                chunks = [doc.texto] if variant == VARIANTS[0] else dividir_em_trechos(doc.texto)
                for index, text in enumerate(chunks):
                    doc_id = doc.doc_id if variant == VARIANTS[0] else f"{doc.doc_id}#chunk-{index:03d}"
                    records.append((doc_id, text, {"source_id": doc.doc_id, "sha256": doc.sha256}))
            collection.upsert(
                ids=[r[0] for r in records], documents=[r[1] for r in records],
                metadatas=[r[2] for r in records],
            )
            collections[(variant, name)] = collection
    return collections


async def run(args) -> int:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    from urllib.parse import urlparse
    from urllib.request import urlopen

    # Só Ollama local: nenhum envio de documentos/credenciais a serviços externos.
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    parsed = urlparse(base_url)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.username or parsed.password:
        raise ValueError("O benchmark requer OLLAMA_BASE_URL local, sem credenciais")
    with urlopen(base_url + "/api/tags", timeout=10) as response:
        installed = {m["name"]: m["digest"] for m in json.load(response)["models"]}
    for model in (args.model, args.judge):
        if model not in installed:
            raise ValueError(f"Modelo não instalado: {model}. Execute ollama pull {model}")
    documents = carregar_documentos()
    cases = load_cases(ROOT / "evals" / "rag_dataset.json", documents)
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit deve ser positivo")
    versions = {package: version(package) for package in (
        "ragas", "langchain-community", "langchain-core", "langchain-ollama",
        "chromadb", "sentence-transformers", "langchain-text-splitters",
    )}
    config = {
        "generator": args.model, "judge": args.judge,
        "model_digests": {m: installed[m] for m in (args.model, args.judge)},
        "embedding": os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        "strictness": args.strictness, "temperature": 0, "seed": 42,
        "num_ctx": 8192, "generator_num_predict": 512, "judge_num_predict": 2048,
        "timeout": args.timeout, "versions": versions, "python": platform.python_version(),
        "top_k": 3, "chunk_size": 400, "chunk_overlap": 80,
        "corpus": {doc.doc_id: {"sha256": doc.sha256, "collections": doc.colecoes} for doc in documents},
        "files": {name: file_hash(ROOT / name) for name in (
            "prompts/morador.txt", "prompts/sindico.txt", "services/llm_service.py",
            "services/rag_retrieval.py", "evals/run_ragas.py", "evals/rag_benchmark.py",
            "evals/ragas_local.py",
        )},
        "relevancy_language_instruction": "Generate the question in Brazilian Portuguese, matching the language of the answer.",
    }
    fingerprint = digest({"config": config, "cases": cases})
    output = Path(args.resume).resolve() if args.resume else ROOT / "evals" / "resultados_ragas" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") / "results.json"
    if args.resume:
        result = json.loads(output.read_text(encoding="utf-8"))
        if result["fingerprint"] != fingerprint:
            raise ValueError("Configuração/código/base mudou. Inicie nova execução, sem --resume.")
    else:
        result = {"schema_version": 1, "started_at": utc_now(), "status": "em_andamento", "fingerprint": fingerprint, "config": config, "cases": cases, "rows": []}
    save_result(output, result)
    print(f"Evidências: {output}", flush=True)

    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    from langchain_ollama import ChatOllama
    from services.llm_service import PROMPT_MORADOR, PROMPT_SINDICO
    embedding = SentenceTransformerEmbeddingFunction(model_name=config["embedding"])
    collections = build_indices(documents, embedding, fingerprint)
    generator = ChatOllama(
        base_url=base_url, model=args.model, temperature=0, seed=42,
        num_ctx=8192, num_predict=512, keep_alive="15m",
        client_kwargs={"timeout": args.timeout}, async_client_kwargs={"timeout": args.timeout},
    )
    selected = cases[:args.limit] if args.limit else cases
    # Gerar todas as respostas primeiro: evita alternar continuamente modelos na memória.
    for index, case in enumerate(selected):
        variants = VARIANTS if index % 2 == 0 else tuple(reversed(VARIANTS))
        for variant in variants:
            if any(r["id"] == case["id"] and r["variant"] == variant for r in result["rows"]):
                continue
            row = {"id": case["id"], "variant": variant, "category": case["category"], "scores": {}, "errors": {}}
            print(f"[GERAR] {case['id']} / {variant}", flush=True)
            try:
                start = time.perf_counter()
                collection = "atendimento" if case["profile"] == "morador" else "sindico"
                retrieved = consultar_trechos(collections[(variant, collection)], case["question"])
                row["retrieval_seconds"] = time.perf_counter() - start
                row["retrieved"] = retrieved
                row["context_chars"] = sum(len(r["texto"]) for r in retrieved)
                sources = {r["metadados"]["source_id"] for r in retrieved}
                row["source_recall"] = len(sources & set(case["source_ids"])) / len(set(case["source_ids"]))
                context = formatar_contexto(retrieved)
                profile = case["profile"]
                inputs = {
                    "system_prompt": (ROOT / "prompts" / f"{profile}.txt").read_text(encoding="utf-8"),
                    "historico": [], "pergunta": case["question"], "contexto": context,
                    "contexto_docs": context, "dados_banco": "Nenhum dado operacional fornecido nesta avaliação documental.",
                }
                prompt = PROMPT_MORADOR if profile == "morador" else PROMPT_SINDICO
                start = time.perf_counter()
                answer = await asyncio.wait_for((prompt | generator).ainvoke(inputs), timeout=args.timeout)
                row["generation_seconds"] = time.perf_counter() - start
                row["response"] = answer.content
                row["usage"] = answer.usage_metadata
                row["done_reason"] = answer.response_metadata.get("done_reason")
                if not answer.content or row["done_reason"] != "stop":
                    raise ValueError("Resposta vazia ou truncada; não será pontuada")
            except Exception as exc:
                row["errors"]["generation"] = type(exc).__name__ + ": " + str(exc)[:400]
            result["rows"].append(row)
            save_result(output, result)

    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.embeddings import Embeddings
    from ragas import SingleTurnSample
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import Faithfulness, ResponseRelevancy, LLMContextPrecisionWithReference, LLMContextRecall
    from ragas.run_config import RunConfig

    class LocalEmbeddings(Embeddings):
        def embed_documents(self, texts):
            return [list(map(float, vector)) for vector in embedding(texts)]
        def embed_query(self, text):
            return self.embed_documents([text])[0]

    class Audit(BaseCallbackHandler):
        def __init__(self):
            self.calls = []
        def on_llm_end(self, response, **kwargs):
            for group in response.generations:
                for generation in group:
                    message = generation.message
                    self.calls.append({
                        "text": generation.text, "usage": message.usage_metadata,
                        "done_reason": message.response_metadata.get("done_reason"),
                    })

    audit = Audit()
    judge = ChatOllama(
        base_url=base_url, model=args.judge, temperature=0, seed=42, reasoning=False,
        num_ctx=8192, num_predict=2048, format="json", keep_alive="15m", callbacks=[audit],
        client_kwargs={"timeout": args.timeout}, async_client_kwargs={"timeout": args.timeout},
    )
    run_config = RunConfig(timeout=args.timeout, max_retries=1, max_workers=1, seed=42)
    wrapped = LangchainLLMWrapper(
        judge, run_config=run_config, bypass_temperature=True,
        is_finished_parser=lambda response: all(
            g.message.response_metadata.get("done_reason") == "stop"
            for group in response.generations for g in group
        ),
    )
    metrics = [
        Faithfulness(llm=wrapped),
        ResponseRelevancy(llm=wrapped, embeddings=LangchainEmbeddingsWrapper(LocalEmbeddings()), strictness=args.strictness),
        LLMContextPrecisionWithReference(llm=wrapped),
        LLMContextRecall(llm=wrapped),
    ]
    metrics[1].question_generation = metrics[1].question_generation.model_copy(deep=True) if hasattr(metrics[1].question_generation, "model_copy") else __import__("copy").deepcopy(metrics[1].question_generation)
    metrics[1].question_generation.instruction += " " + config["relevancy_language_instruction"]
    from evals.ragas_local import OllamaStructuredPrompt
    for metric in metrics:
        metric.set_prompts(**{
            name: OllamaStructuredPrompt(prompt, judge)
            for name, prompt in metric.get_prompts().items()
        })
    cases_by_id = {case["id"]: case for case in selected}
    for row in result["rows"]:
        if row["id"] not in cases_by_id or "generation" in row["errors"]:
            continue
        case = cases_by_id[row["id"]]
        sample = SingleTurnSample(
            user_input=case["question"], response=row["response"],
            retrieved_contexts=[r["texto"] for r in row["retrieved"]], reference=case["reference"],
        )
        for name, metric in zip(METRICS, metrics, strict=True):
            if name in row["scores"]:
                continue
            print(f"[RAGAS] {row['id']} / {row['variant']} / {name}", flush=True)
            audit.calls = []
            start = time.perf_counter()
            try:
                score = float(await metric.single_turn_ascore(sample, timeout=args.timeout))
                if not math.isfinite(score):
                    raise ValueError("RAGAS retornou nota não finita")
                row["scores"][name] = score
            except Exception as exc:
                row["scores"][name] = None
                row["errors"][name] = type(exc).__name__ + ": " + str(exc)[:400]
            row.setdefault("judge_audit", {})[name] = {"seconds": time.perf_counter() - start, "calls": list(audit.calls)}
            save_result(output, result)
    all_done = len(result["rows"]) == len(cases) * len(VARIANTS) and all(
        "generation" in r["errors"] or all(m in r["scores"] for m in METRICS) for r in result["rows"]
    )
    failures = any(r["errors"] for r in result["rows"])
    result["status"] = ("concluido_com_falhas" if failures else "concluido") if all_done else "parcial"
    save_result(output, result)
    print(f"Estado: {result['status']}. Relatório: {output.with_suffix('.md')}", flush=True)
    return 2 if failures or not all_done else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="llama3.2:3b")
    parser.add_argument("--judge", default="qwen3:4b")
    parser.add_argument("--strictness", type=int, choices=(1, 3), default=3)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--limit", type=int, help="Smoke test: limita casos e marca o relatório como parcial")
    parser.add_argument("--resume", help="Retoma results.json compatível, sem repetir chamadas registradas")
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error("--timeout deve ser positivo")
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        print("Interrompido. Use --resume com o caminho mostrado para continuar.", flush=True)
        return 130
    except Exception as exc:
        print(f"Falha: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
