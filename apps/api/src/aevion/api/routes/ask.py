"""POST /api/ask: the agent over HTTP (SPEC section 8), and POST /api/ask/stream, the same
answer with live progress as Server-Sent Events."""

import json
import queue
import threading
import time
from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from aevion.agent.cache import cached_answer
from aevion.agent.loop import AskResponse, Event, ask
from aevion.api.deps import get_db
from aevion.api.limits import ASK_RULES, RateLimiter, enforce
from aevion.config import Settings
from aevion.graph.client import GraphNotFoundError, OrgGraph
from aevion.graph.naming import graph_name_for
from aevion.llm.client import BudgetExceededError, LLMClient, LLMError
from aevion.llm.factory import llm_client

router = APIRouter(prefix="/api", tags=["ask"])
# Shared by every route that spends LLM money (ask, triage dry runs).
ask_limiter = RateLimiter(ASK_RULES)


class AskRequest(BaseModel):
    org: str = Field(min_length=1, max_length=39)
    question: str = Field(min_length=1, max_length=500)


@lru_cache(maxsize=1)
def _settings() -> Settings:
    return Settings()


def get_llm() -> LLMClient:
    return llm_client(_settings())


def _graph(org: str, db: Any) -> OrgGraph:
    try:
        return OrgGraph(db, graph_name_for(org))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _failure(exc: Exception, org: str) -> HTTPException:
    if isinstance(exc, GraphNotFoundError):
        return HTTPException(status_code=404, detail=f"No graph for org {org!r}")
    if isinstance(exc, BudgetExceededError):
        return HTTPException(status_code=503, detail="Aevion's question budget is used up for now.")
    if isinstance(exc, LLMError):
        return HTTPException(
            status_code=503, detail="The language model is unavailable. Try again shortly."
        )
    raise exc


def _elapsed(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


@router.post("/ask", response_model=AskResponse)
def ask_route(
    body: AskRequest,
    request: Request,
    db: Annotated[Any, Depends(get_db)],
    llm: Annotated[LLMClient, Depends(get_llm)],
) -> AskResponse:
    graph = _graph(body.org, db)
    question = body.question.strip()
    started = time.perf_counter()
    try:
        # Warmed hero answers cost nothing, so they come first and don't count toward the limit.
        if hit := cached_answer(graph, question):
            return hit.model_copy(update={"elapsed_ms": _elapsed(started)})
        enforce(ask_limiter, request, _settings().proxy_secret)
        answer = ask(graph, llm, _settings().agent_model, body.org, question)
        return answer.model_copy(update={"elapsed_ms": _elapsed(started)})
    except (GraphNotFoundError, LLMError) as exc:
        raise _failure(exc, body.org) from exc


@router.post("/ask/stream")
def ask_stream_route(
    body: AskRequest,
    request: Request,
    db: Annotated[Any, Depends(get_db)],
    llm: Annotated[LLMClient, Depends(get_llm)],
) -> StreamingResponse:
    """Server-Sent Events: `tool`, `tool_done` and `writing` while the agent works, then one
    `answer` (the /api/ask response) or one `error` ({status, detail}). The rate limit is
    checked before the stream starts, so a limited request still gets a plain 429."""
    graph = _graph(body.org, db)
    question = body.question.strip()
    started = time.perf_counter()
    try:
        hit = cached_answer(graph, question)
    except GraphNotFoundError as exc:
        raise _failure(exc, body.org) from exc
    if hit is None:
        enforce(ask_limiter, request, _settings().proxy_secret)

    def events() -> Iterator[str]:
        if hit is not None:
            yield _sse({"type": "cached"})
            answer = hit.model_copy(update={"elapsed_ms": _elapsed(started)})
            yield _sse({"type": "answer", "answer": answer.model_dump(mode="json")})
            return
        updates: queue.Queue[Event | None] = queue.Queue()

        def work() -> None:
            try:
                result = ask(graph, llm, _settings().agent_model, body.org, question, updates.put)
                result = result.model_copy(update={"elapsed_ms": _elapsed(started)})
                updates.put({"type": "answer", "answer": result.model_dump(mode="json")})
            except (GraphNotFoundError, LLMError) as exc:
                failure = _failure(exc, body.org)
                updates.put(
                    {"type": "error", "status": failure.status_code, "detail": failure.detail}
                )
            except Exception:  # never end the stream silently: say something went wrong
                updates.put(
                    {
                        "type": "error",
                        "status": 500,
                        "detail": "Something went wrong answering that.",
                    }
                )
                raise
            finally:
                updates.put(None)

        threading.Thread(target=work, daemon=True).start()
        while (event := updates.get()) is not None:
            yield _sse(event)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


def _sse(event: Event) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"
