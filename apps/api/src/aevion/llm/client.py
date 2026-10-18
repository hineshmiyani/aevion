"""OpenRouter chat client: one code path for every model (ADR-0009, ADR-0010).

Guardrails from ADR-0009 live here so no caller can skip them:
- every response is cached by a hash of the full request, so re-runs cost $0;
- every call is written to a spend ledger, with reasoning tokens counted;
- calls are refused once the ledger reaches the budget.
"""

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

MAX_ATTEMPTS = 4


class LLMError(Exception):
    pass


class BudgetExceededError(LLMError):
    """The ledger has reached the configured budget; no more paid calls."""


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    cost_usd: float = 0.0


@dataclass(frozen=True)
class ChatResult:
    model: str
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: Usage = Usage()
    cached: bool = False
    finish_reason: str = ""  # "length" means max_tokens cut the reply off

    def tool_arguments(self) -> list[tuple[str, dict[str, Any]]]:
        """(tool name, parsed arguments) for each tool call; bad JSON becomes {}."""
        calls = []
        for call in self.tool_calls:
            function = call.get("function", {})
            try:
                arguments = json.loads(function.get("arguments") or "{}")
            except json.JSONDecodeError:
                arguments = {}
            calls.append((function.get("name", ""), arguments))
        return calls


class Ledger:
    """Append-only JSONL record of every LLM call and what it cost."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()  # extraction records from several worker threads

    def record(self, model: str, usage: Usage, cached: bool, purpose: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "model": model,
            "purpose": purpose,
            "cached": cached,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "reasoning_tokens": usage.reasoning_tokens,
            "cost_usd": 0.0 if cached else usage.cost_usd,
        }
        with self._lock, self.path.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]

    def total_usd(self) -> float:
        return round(sum(float(e["cost_usd"]) for e in self.entries()), 6)


class LLMClient:
    def __init__(
        self,
        api_key: str | None,
        *,
        base_url: str,
        cache_dir: Path | None,
        ledger: Ledger,
        budget_usd: float,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._api_key = api_key
        self._cache_dir = cache_dir
        self.ledger = ledger
        self.budget_usd = budget_usd
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
            headers={
                "X-Title": "Aevion",
                "HTTP-Referer": "https://github.com/hineshmiyani/aevion-company-brain",
            },
        )

    def chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1200,
        response_format: dict[str, Any] | None = None,
        purpose: str = "chat",
    ) -> ChatResult:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "usage": {"include": True},  # OpenRouter returns the real cost in `usage.cost`
        }
        if tools:
            payload["tools"] = tools
        if response_format:
            payload["response_format"] = response_format

        cache_path = self._cache_path(payload)
        if cache_path and cache_path.exists():
            result = _parse(json.loads(cache_path.read_text()), model, cached=True)
            self.ledger.record(model, result.usage, cached=True, purpose=purpose)
            return result

        if self.ledger.total_usd() >= self.budget_usd:
            spent = self.ledger.total_usd()
            raise BudgetExceededError(
                f"LLM spend ${spent:.2f} reached the ${self.budget_usd:.2f} budget"
            )
        if not self._api_key:
            raise LLMError("OPENROUTER_API_KEY is not set")

        body = self._post(payload)
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(body))
        result = _parse(body, model, cached=False)
        self.ledger.record(model, result.usage, cached=False, purpose=purpose)
        return result

    def close(self) -> None:
        self._http.close()

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        for attempt in range(1, MAX_ATTEMPTS + 1):
            response = self._http.post("/chat/completions", json=payload, headers=headers)
            if response.status_code in (429, 500, 502, 503, 504) and attempt < MAX_ATTEMPTS:
                retry_after = float(response.headers.get("retry-after") or 2**attempt)
                time.sleep(min(retry_after, 30))
                continue
            if response.status_code >= 400:
                raise LLMError(f"OpenRouter {response.status_code}: {response.text[:300]}")
            body: dict[str, Any] = response.json()
            if body.get("error"):
                raise LLMError(f"OpenRouter error: {json.dumps(body['error'])[:300]}")
            return body
        raise LLMError(f"OpenRouter failed after {MAX_ATTEMPTS} attempts")

    def _cache_path(self, payload: dict[str, Any]) -> Path | None:
        if self._cache_dir is None:
            return None
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:32]
        return self._cache_dir / f"{digest}.json"


def _parse(body: dict[str, Any], model: str, *, cached: bool) -> ChatResult:
    choice = (body.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    usage = body.get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    return ChatResult(
        model=body.get("model", model),
        content=message.get("content") or "",
        tool_calls=message.get("tool_calls") or [],
        usage=Usage(
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            reasoning_tokens=int(details.get("reasoning_tokens") or 0),
            cost_usd=float(usage.get("cost") or 0.0),
        ),
        cached=cached,
        finish_reason=choice.get("finish_reason") or "",
    )
