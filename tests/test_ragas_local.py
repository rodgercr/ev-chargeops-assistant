"""Contrato do adaptador: usa schema nativo e nunca aceita JSON inválido/truncado."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
import os

import pytest
from pydantic import BaseModel

os.environ["RAGAS_DO_NOT_TRACK"] = "true"
pytest.importorskip("ragas")
from ragas.prompt import PydanticPrompt
from evals.ragas_local import OllamaStructuredPrompt


class Input(BaseModel):
    question: str


class Output(BaseModel):
    verdict: int


class ExamplePrompt(PydanticPrompt[Input, Output]):
    instruction = "Judge the input."
    input_model = Input
    output_model = Output


def make_judge(reason="stop", parsed=None, error=None):
    judge = Mock()
    chain = Mock()
    chain.ainvoke = AsyncMock(return_value={
        "raw": SimpleNamespace(response_metadata={"done_reason": reason}),
        "parsed": parsed, "parsing_error": error,
    })
    judge.with_structured_output.return_value = chain
    return judge, chain


def test_adapter_uses_original_schema_and_exact_number_of_generations():
    judge, chain = make_judge(parsed=Output(verdict=1))
    prompt = OllamaStructuredPrompt(ExamplePrompt(), judge)
    results = asyncio.run(prompt.generate_multiple(None, Input(question="Recarga?"), n=3))
    assert len(results) == 3
    assert chain.ainvoke.await_count == 3
    judge.with_structured_output.assert_called_once_with(Output, method="json_schema", include_raw=True)
    assert all(result.verdict == 1 for result in results)


@pytest.mark.parametrize("reason,parsed,error", [
    ("length", Output(verdict=1), None), ("stop", None, "parse error"), ("stop", None, None),
])
def test_adapter_rejects_incomplete_results(reason, parsed, error):
    judge, _ = make_judge(reason=reason, parsed=parsed, error=error)
    prompt = OllamaStructuredPrompt(ExamplePrompt(), judge)
    with pytest.raises(ValueError):
        asyncio.run(prompt.generate_multiple(None, Input(question="Recarga?")))
