"""Avaliação Sprint 4: dois prompts, dois geradores, base fixa e notas RAGAS reais."""
import os
os.environ["RAGAS_DO_NOT_TRACK"] = "true"
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from importlib.metadata import version
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
from src.rag.loader import carregar_documentos
from src.rag.chunking import criar_trechos
from src.rag.vector_store import nome_indice, indexar
from src.rag.retriever import recuperar, formatar_contexto
from src.rag.prompt_rag import prompt, validar_citacoes
from evals.rag_benchmark import load_cases

def salvar(caminho, dados):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

async def executar(args):
    from langchain_ollama import ChatOllama
    from langchain_core.callbacks import BaseCallbackHandler
    from ragas import SingleTurnSample
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.metrics import Faithfulness, ResponseRelevancy
    from ragas.run_config import RunConfig
    from src.rag.embeddings import modelo_embeddings
    from evals.ragas_local import OllamaStructuredPrompt
    from urllib.request import urlopen
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    from urllib.parse import urlparse
    if urlparse(base).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Avaliação permite somente Ollama local")
    with urlopen(base + "/api/tags", timeout=10) as response:
        models = {m["name"]: m["digest"] for m in json.load(response)["models"]}
    for m in [*args.models, args.judge, "nomic-embed-text:latest"]:
        if m not in models:
            raise ValueError(f"Modelo ausente: {m}")
    docs = carregar_documentos()
    cases = load_cases(ROOT / "evals" / "rag_dataset_sprint4.json", docs)
    iterations = {"v1": {"k": 2}, "v2": {"k": 4}}
    config = {
        "models": args.models, "judge": args.judge, "temperature": 0, "top_p": .9,
        "max_tokens": 512, "judge_max_tokens": 2048, "num_ctx": 8192, "seed": 42,
        "embedding": "nomic-embed-text:latest", "strictness": 3, "iterations": iterations,
        "chunk_size": 900, "overlap": 150, "model_digests": models,
        "corpus": {d.doc_id: d.sha256 for d in docs},
        "files": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted((ROOT / "src" / "rag").glob("*")) if p.is_file()},
        "versions": {p: version(p) for p in ("ragas", "chromadb", "langchain-ollama", "langchain-core")},
    }
    fingerprint = hashlib.sha256(json.dumps({"config": config, "cases": cases}, sort_keys=True).encode()).hexdigest()
    out = Path(args.output)
    if out.exists():
        result = json.loads(out.read_text(encoding="utf-8"))
        if result["fingerprint"] != fingerprint:
            raise ValueError("Não sobrescrever avaliação de configuração diferente; use outro --output")
    else:
        result = {"started_at": datetime.now(timezone.utc).isoformat(), "fingerprint": fingerprint,
                  "config": config, "cases": cases, "rows": [], "status": "em_andamento"}
    salvar(out, result)
    regs = criar_trechos(docs)
    col = indexar(regs, nome_indice(regs))
    for model in args.models:
        llm = ChatOllama(model=model, base_url=base, temperature=0, top_p=.9, seed=42,
                         num_predict=512, num_ctx=8192, reasoning=False,
                         client_kwargs={"timeout": 180}, async_client_kwargs={"timeout": 180})
        for case in cases:
            for iteration, settings in iterations.items():
                if any(r["model"] == model and r["id"] == case["id"] and r["iteration"] == iteration for r in result["rows"]):
                    continue
                row = {"id": case["id"], "model": model, "iteration": iteration, "scores": {}, "errors": {}}
                print(f"GERAR {model} {iteration} {case['id']}", flush=True)
                try:
                    start = time.perf_counter()
                    chunks = recuperar(case["question"], case["profile"], settings["k"], col)
                    row["retrieved"] = chunks
                    row["retrieval_seconds"] = time.perf_counter() - start
                    fontes = list(dict.fromkeys(c["metadados"]["source_id"] for c in chunks))
                    row["source_recall"] = len(set(fontes) & set(case["source_ids"])) / len(set(case["source_ids"]))
                    start = time.perf_counter()
                    msg = await (prompt(iteration) | llm).ainvoke({"contexto": formatar_contexto(chunks), "pergunta": case["question"]})
                    if msg.response_metadata.get("done_reason") != "stop":
                        raise ValueError("Resposta truncada")
                    row["raw_response"] = msg.content
                    row["response"] = validar_citacoes(msg.content, fontes)
                    row["citation_present"] = "[Fonte:" in row["response"]
                    row["generation_seconds"] = time.perf_counter() - start
                    row["usage"] = msg.usage_metadata
                except Exception as exc:
                    row["errors"]["generation"] = type(exc).__name__ + ": " + str(exc)[:300]
                result["rows"].append(row)
                salvar(out, result)
    class Audit(BaseCallbackHandler):
        def __init__(self):
            self.calls = []
        def on_llm_end(self, response, **kwargs):
            for group in response.generations:
                for generation in group:
                    self.calls.append({"text": generation.text, "usage": generation.message.usage_metadata})
    audit = Audit()
    judge = ChatOllama(model=args.judge, base_url=base, temperature=0, top_p=.9, seed=42,
                       num_ctx=8192, num_predict=2048, reasoning=False, callbacks=[audit],
                       client_kwargs={"timeout": 180}, async_client_kwargs={"timeout": 180})
    wrapped = LangchainLLMWrapper(judge, run_config=RunConfig(timeout=180, max_retries=1, seed=42),
                                   bypass_temperature=True)
    metrics = [Faithfulness(llm=wrapped),
               ResponseRelevancy(llm=wrapped, embeddings=LangchainEmbeddingsWrapper(modelo_embeddings()), strictness=3)]
    for metric in metrics:
        metric.set_prompts(**{name: OllamaStructuredPrompt(p, judge) for name, p in metric.get_prompts().items()})
    byid = {c["id"]: c for c in cases}
    for row in result["rows"]:
        if "generation" in row["errors"]:
            continue
        case = byid[row["id"]]
        sample = SingleTurnSample(user_input=case["question"], response=row["response"],
                                  retrieved_contexts=[c["texto"] for c in row["retrieved"]], reference=case["reference"])
        for name, metric in zip(("faithfulness", "answer_relevancy"), metrics):
            if name in row["scores"]:
                continue
            print(f"RAGAS {row['model']} {row['iteration']} {row['id']} {name}", flush=True)
            audit.calls = []
            try:
                score = float(await metric.single_turn_ascore(sample, timeout=180))
                if not math.isfinite(score):
                    raise ValueError("Nota não finita")
                row["scores"][name] = score
            except Exception as exc:
                row["scores"][name] = None
                row["errors"][name] = type(exc).__name__ + ": " + str(exc)[:300]
            row.setdefault("audit", {})[name] = list(audit.calls)
            salvar(out, result)
    result["status"] = "concluido_com_falhas" if any(r["errors"] for r in result["rows"]) else "concluido"
    salvar(out, result)
    print(result["status"], out, flush=True)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--models", nargs="+", default=["llama3.2:3b", "qwen3:4b"])
    p.add_argument("--judge", default="qwen3:4b")
    p.add_argument("--output", default=str(ROOT / "evals" / "sprint4" / "results.json"))
    asyncio.run(executar(p.parse_args()))
