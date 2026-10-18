"""The streaming ask endpoint and graph stats, with the model scripted (no network)."""

import json
import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest
from falkordb import FalkorDB
from fastapi.testclient import TestClient

from aevion.agent.cache import store_answer
from aevion.agent.loop import AskResponse, Citation
from aevion.api.main import app, get_db
from aevion.api.routes import stats as stats_routes
from aevion.api.routes.ask import get_llm
from aevion.graph.client import OrgGraph
from aevion.graph.naming import graph_name_for
from aevion.graph.schema import bootstrap
from aevion.llm.client import Ledger, LLMClient
from tests.integration.conftest import load_fixture_pages

pytestmark = pytest.mark.integration

REPO = "FalkorDB/falkordb-py"


def _scripted(tmp_path: Path) -> LLMClient:
    replies = [
        {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "c0",
                                "type": "function",
                                "function": {
                                    "name": "experts_for",
                                    "arguments": json.dumps(
                                        {"component": "falkordb", "repo": REPO}
                                    ),
                                },
                            }
                        ],
                    }
                }
            ],
            "usage": {"cost": 0.0001},
        },
        {"choices": [{"message": {"content": "**alice** [2]."}}], "usage": {"cost": 0.0001}},
    ]
    seen: list[int] = []

    def openrouter(request: httpx.Request) -> httpx.Response:
        seen.append(1)
        return httpx.Response(200, json=replies[min(len(seen), len(replies)) - 1])

    return LLMClient(
        "sk-or-test",
        base_url="https://openrouter.test/api/v1",
        cache_dir=None,
        ledger=Ledger(tmp_path / "ledger.jsonl"),
        budget_usd=1.0,
        transport=httpx.MockTransport(openrouter),
    )


def _events(text: str) -> list[dict[str, Any]]:
    return [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ")]


@pytest.fixture
def org(db: FalkorDB, pr_page: dict[str, Any], issue_page: dict[str, Any], tmp_path: Path):
    name = f"aevion-test-{uuid.uuid4().hex[:8]}"
    graph = OrgGraph(db, graph_name_for(name))
    bootstrap(graph)
    load_fixture_pages(graph, pr_page, issue_page)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm] = lambda: _scripted(tmp_path)
    yield name, graph
    app.dependency_overrides.clear()
    graph.delete()


def test_stream_reports_each_tool_then_the_answer(org: tuple[str, OrgGraph]) -> None:
    name, _graph = org
    response = TestClient(app).post(
        "/api/ask/stream", json={"org": name, "question": "Who knows it?"}
    )
    assert response.status_code == 200 and response.headers["content-type"].startswith(
        "text/event-stream"
    )
    events = _events(response.text)
    assert [e["type"] for e in events] == ["tool", "tool_done", "writing", "answer"]
    assert events[0]["tool"] == "experts_for" and events[1]["rows"] > 0 and events[1]["ms"] >= 0
    answer = events[-1]["answer"]
    assert (
        answer["answer"] == "**alice** [1]."
        and answer["cached"] is False
        and answer["elapsed_ms"] >= 0
    )


def test_stream_serves_cached_answers_at_once(org: tuple[str, OrgGraph]) -> None:
    name, graph = org
    store_answer(
        graph,
        "Who knows falkordb-py?",
        AskResponse(
            answer="**alice** [1].",
            citations=[Citation(n=1, node_id="Person:alice")],
            model="m",
            cached=False,
        ),
    )
    response = TestClient(app).post(
        "/api/ask/stream", json={"org": name, "question": "who knows falkordb-py"}
    )
    events = _events(response.text)
    assert [e["type"] for e in events] == ["cached", "answer"]
    assert events[1]["answer"]["cached"] is True and events[1]["answer"]["elapsed_ms"] >= 0


def test_stats_counts_the_graph(org: tuple[str, OrgGraph]) -> None:
    name, graph = org
    stats_routes._cache.clear()
    body = TestClient(app).get("/api/stats", params={"org": name}).json()
    nodes = graph.ro_query("MATCH (n) RETURN count(n)").rows[0][0]
    assert body["nodes"] == nodes and body["repos"] == 1 and body["pull_requests"] == 3
    assert body["edges"] > 0 and body["decisions"] == 0
    assert TestClient(app).get("/api/stats", params={"org": "no-such-org"}).status_code == 404
