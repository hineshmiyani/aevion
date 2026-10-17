"""LLM client behaviour against a stubbed OpenRouter (no network, no key spent)."""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from aevion.llm.client import BudgetExceededError, Ledger, LLMClient, LLMError

COMPLETION = {
    "model": "anthropic/claude-haiku-5.5",
    "choices": [
        {
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "experts_for",
                            "arguments": '{"component": "falkordb"}',
                        },
                    }
                ],
            }
        }
    ],
    "usage": {
        "prompt_tokens": 1500,
        "completion_tokens": 120,
        "completion_tokens_details": {"reasoning_tokens": 40},
        "cost": 0.00021,
    },
}


class StubOpenRouter:
    """Counts requests and plays back responses (status, body) in order, then repeats the last."""

    def __init__(self, *responses: tuple[int, dict[str, Any]]) -> None:
        self.responses = list(responses) or [(200, COMPLETION)]
        self.requests: list[dict[str, Any]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        status, body = self.responses[min(len(self.requests) - 1, len(self.responses) - 1)]
        return httpx.Response(status, json=body, headers={"retry-after": "0"})


def _client(
    tmp_path: Path, stub: StubOpenRouter, budget: float = 12.0, key: str | None = "sk-or-test"
) -> LLMClient:
    return LLMClient(
        key,
        base_url="https://openrouter.test/api/v1",
        cache_dir=tmp_path / "cache",
        ledger=Ledger(tmp_path / "ledger.jsonl"),
        budget_usd=budget,
        transport=httpx.MockTransport(stub),
    )


MESSAGES = [{"role": "user", "content": "Who knows falkordb-py?"}]


def test_parses_tool_calls_usage_and_cost(tmp_path: Path) -> None:
    stub = StubOpenRouter()
    result = _client(tmp_path, stub).chat(
        "anthropic/claude-haiku-5.5", MESSAGES, tools=[{"type": "function"}]
    )
    assert result.tool_arguments() == [("experts_for", {"component": "falkordb"})]
    assert result.usage.reasoning_tokens == 40
    assert result.usage.cost_usd == pytest.approx(0.00021)
    assert stub.requests[0]["usage"] == {"include": True}  # ask OpenRouter for the real cost


def test_identical_request_is_served_from_cache_for_free(tmp_path: Path) -> None:
    stub = StubOpenRouter()
    client = _client(tmp_path, stub)
    first = client.chat("anthropic/claude-haiku-5.5", MESSAGES)
    second = client.chat("anthropic/claude-haiku-5.5", MESSAGES)
    assert len(stub.requests) == 1
    assert not first.cached and second.cached
    assert client.ledger.total_usd() == pytest.approx(0.00021)  # the cache hit cost $0


def test_different_request_is_not_cached(tmp_path: Path) -> None:
    stub = StubOpenRouter()
    client = _client(tmp_path, stub)
    client.chat("anthropic/claude-haiku-5.5", MESSAGES)
    client.chat("anthropic/claude-haiku-5.5", [{"role": "user", "content": "Something else"}])
    assert len(stub.requests) == 2


def test_budget_guard_refuses_paid_calls_but_allows_cache_hits(tmp_path: Path) -> None:
    stub = StubOpenRouter()
    client = _client(tmp_path, stub, budget=0.0002)  # one call (0.00021) exhausts it
    client.chat("anthropic/claude-haiku-5.5", MESSAGES)
    with pytest.raises(BudgetExceededError):
        client.chat("anthropic/claude-haiku-5.5", [{"role": "user", "content": "new question"}])
    assert client.chat("anthropic/claude-haiku-5.5", MESSAGES).cached  # cache still works
    assert len(stub.requests) == 1


def test_retries_rate_limits_then_succeeds(tmp_path: Path) -> None:
    stub = StubOpenRouter((429, {"error": {"message": "slow down"}}), (200, COMPLETION))
    result = _client(tmp_path, stub).chat("anthropic/claude-haiku-5.5", MESSAGES)
    assert len(stub.requests) == 2 and result.usage.cost_usd > 0


def test_errors_are_raised_not_cached(tmp_path: Path) -> None:
    stub = StubOpenRouter((400, {"error": {"message": "bad model"}}))
    client = _client(tmp_path, stub)
    with pytest.raises(LLMError, match="400"):
        client.chat("nope/model", MESSAGES)
    assert not (tmp_path / "cache").exists() or not any((tmp_path / "cache").iterdir())


def test_missing_key_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(LLMError, match="OPENROUTER_API_KEY"):
        _client(tmp_path, StubOpenRouter(), key=None).chat("anthropic/claude-haiku-5.5", MESSAGES)


def test_bad_tool_arguments_become_empty(tmp_path: Path) -> None:
    body = json.loads(json.dumps(COMPLETION))
    body["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = "{not json"
    result = _client(tmp_path, StubOpenRouter((200, body))).chat("m", MESSAGES)
    assert result.tool_arguments() == [("experts_for", {})]
