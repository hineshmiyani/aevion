"""Cached hero answers live in the graph and skip the model and the rate limit."""

import json
import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest
from falkordb import FalkorDB
from fastapi.testclient import TestClient

from aevion.agent.cache import cached_answer, question_key, store_answer
from aevion.agent.loop import AskResponse, Citation
from aevion.api.limits import RateLimiter
from aevion.api.main import app, get_db
from aevion.api.routes import ask as ask_routes
from aevion.api.routes.ask import get_llm
from aevion.graph.client import OrgGraph
from aevion.graph.naming import graph_name_for
from aevion.graph.schema import bootstrap
from aevion.llm.client import Ledger, LLMClient
from tests.integration.conftest import load_fixture_pages

pytestmark = pytest.mark.integration

REPO = "FalkorDB/falkordb-py"
ANSWER = AskResponse(
    answer="**alice** [1], via [2].",
    citations=[
        Citation(n=1, node_id="Person:alice"),
        Citation(n=2, node_id=f"PullRequest:{REPO}#101"),
    ],
    model="m",
    cached=False,
)


def test_question_key_ignores_case_spacing_and_punctuation() -> None:
    assert question_key("Who knows  falkordb-py?") == question_key("who knows falkordb-py")


def test_store_and_read_back_with_cites_edges(fixture_graph: OrgGraph) -> None:
    store_answer(fixture_graph, "Who knows falkordb-py?", ANSWER)
    store_answer(fixture_graph, "Who knows falkordb-py?", ANSWER)  # idempotent
    hit = cached_answer(fixture_graph, "who knows falkordb-py")
    assert hit and hit.cached and hit.answer == ANSWER.answer
    cited = fixture_graph.ro_query(
        "MATCH (:CachedAnswer)-[:CITES]->(n) RETURN labels(n)[0], count(*) ORDER BY labels(n)[0]"
    ).rows
    assert cited == [["Person", 1], ["PullRequest", 1]]
    assert cached_answer(fixture_graph, "Something nobody warmed") is None


def test_cache_hits_skip_the_model_and_the_limit(
    db: FalkorDB,
    pr_page: dict[str, Any],
    issue_page: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    org = f"aevion-test-{uuid.uuid4().hex[:8]}"
    graph = OrgGraph(db, graph_name_for(org))
    bootstrap(graph)
    load_fixture_pages(graph, pr_page, issue_page)
    store_answer(graph, "Who knows falkordb-py?", ANSWER)
    calls: list[Any] = []

    def openrouter(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        body = {"choices": [{"message": {"content": "Live answer."}}], "usage": {"cost": 0.0001}}
        return httpx.Response(200, json=body)

    client = LLMClient(
        "sk-or-test",
        base_url="https://openrouter.test/api/v1",
        cache_dir=None,
        ledger=Ledger(tmp_path / "ledger.jsonl"),
        budget_usd=1.0,
        transport=httpx.MockTransport(openrouter),
    )
    monkeypatch.setattr(ask_routes, "ask_limiter", RateLimiter(((1, 60.0),)))
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm] = lambda: client
    http = TestClient(app)
    try:
        for _ in range(3):  # cached: no model call, never limited
            hit = http.post("/api/ask", json={"org": org, "question": "who knows falkordb-py"})
            assert hit.status_code == 200 and hit.json()["cached"] is True
        assert calls == []
        live = http.post("/api/ask", json={"org": org, "question": "Anything new?"})
        assert live.status_code == 200 and live.json()["cached"] is False
        limited = http.post("/api/ask", json={"org": org, "question": "And again?"})
        assert limited.status_code == 429 and int(limited.headers["Retry-After"]) > 0
    finally:
        app.dependency_overrides.clear()
        graph.delete()
