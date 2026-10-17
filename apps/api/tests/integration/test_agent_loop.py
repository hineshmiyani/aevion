"""The agent loop on the fixture graph, with a scripted model (no network, no key spent)."""

import json
import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest
from falkordb import FalkorDB
from fastapi.testclient import TestClient

from aevion.agent.loop import MAX_TOOL_CALLS, ask, tool_specs
from aevion.api.main import app, get_db
from aevion.api.routes.ask import get_llm
from aevion.graph.client import OrgGraph
from aevion.graph.naming import graph_name_for
from aevion.graph.schema import bootstrap
from aevion.llm.client import Ledger, LLMClient
from tests.integration.conftest import load_fixture_pages

pytestmark = pytest.mark.integration

REPO = "FalkorDB/falkordb-py"
EXPERTS_CALL = {
    "name": "experts_for",
    "arguments": json.dumps({"component": "falkordb", "repo": REPO}),
}


def tool_call(*functions: dict[str, Any]) -> dict[str, Any]:
    calls = [
        {"id": f"call_{i}", "type": "function", "function": f} for i, f in enumerate(functions)
    ]
    return {
        "choices": [{"message": {"content": "", "tool_calls": calls}}],
        "usage": {"cost": 0.0001},
    }


def final(text: str) -> dict[str, Any]:
    return {"choices": [{"message": {"content": text}}], "usage": {"cost": 0.0001}}


class ScriptedModel:
    """Plays back replies in order (repeating the last) and records every request."""

    def __init__(self, *replies: dict[str, Any]) -> None:
        self.replies = list(replies)
        self.requests: list[dict[str, Any]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        return httpx.Response(
            200, json=self.replies[min(len(self.requests), len(self.replies)) - 1]
        )


def client_for(model: ScriptedModel, tmp_path: Path, budget: float = 1.0) -> LLMClient:
    return LLMClient(
        "sk-or-test",
        base_url="https://openrouter.test/api/v1",
        cache_dir=None,  # every call reaches the script
        ledger=Ledger(tmp_path / "ledger.jsonl"),
        budget_usd=budget,
        transport=httpx.MockTransport(model),
    )


def test_tool_specs_cover_every_tool() -> None:
    names = [spec["function"]["name"] for spec in tool_specs()]
    assert names == ["experts_for", "decision_trail", "area_history", "related_work", "catch_up"]
    assert all(spec["function"]["parameters"]["type"] == "object" for spec in tool_specs())


def test_tool_call_then_cited_answer(fixture_graph: OrgGraph, tmp_path: Path) -> None:
    # experts_for numbers its evidence: [1] Component, [2] alice, [3] PR 101, ...
    model = ScriptedModel(
        tool_call(EXPERTS_CALL), final("**alice** knows it best [2], from [3]. Also **bob** [5].")
    )
    response = ask(
        fixture_graph, client_for(model, tmp_path), "m", "FalkorDB", "Who knows falkordb-py?"
    )

    assert [c.tool for c in response.tool_calls] == ["experts_for"]
    assert response.answer == "**alice** knows it best [1], from [2]. Also **bob** [3]."
    assert [c.node_id for c in response.citations] == [
        "Person:alice",
        f"PullRequest:{REPO}#101",
        "Person:bob",
    ]
    assert response.evidence.edges and response.cypher
    tool_message = model.requests[1]["messages"][-1]
    assert tool_message["role"] == "tool" and "[2] Person: alice" in tool_message["content"]


def test_bad_tool_calls_are_reported_back_to_the_model(
    fixture_graph: OrgGraph, tmp_path: Path
) -> None:
    model = ScriptedModel(
        tool_call(
            {"name": "drop_database", "arguments": "{}"}, {"name": "catch_up", "arguments": "{}"}
        ),
        final("I couldn't work that out."),
    )
    response = ask(fixture_graph, client_for(model, tmp_path), "m", "FalkorDB", "Delete everything")
    tool_messages = [m["content"] for m in model.requests[1]["messages"] if m["role"] == "tool"]
    assert "no tool called 'drop_database'" in tool_messages[0]
    assert "invalid arguments for catch_up" in tool_messages[1]
    assert response.answer == "I couldn't work that out." and response.citations == []


def test_tool_calls_are_capped(fixture_graph: OrgGraph, tmp_path: Path) -> None:
    model = ScriptedModel(tool_call(EXPERTS_CALL))  # would call tools forever
    response = ask(fixture_graph, client_for(model, tmp_path), "m", "FalkorDB", "Who knows?")
    assert len(response.tool_calls) == MAX_TOOL_CALLS
    assert "tools" not in model.requests[-1]  # the final request forces an answer


def test_unknown_citations_are_dropped(fixture_graph: OrgGraph, tmp_path: Path) -> None:
    model = ScriptedModel(final("Nothing here [9]."))
    response = ask(fixture_graph, client_for(model, tmp_path), "m", "FalkorDB", "Hello?")
    assert response.answer == "Nothing here." and response.citations == []


def test_ask_endpoint(
    db: FalkorDB, pr_page: dict[str, Any], issue_page: dict[str, Any], tmp_path: Path
) -> None:
    org = f"aevion-test-{uuid.uuid4().hex[:8]}"
    graph = OrgGraph(db, graph_name_for(org))
    bootstrap(graph)
    load_fixture_pages(graph, pr_page, issue_page)
    model = ScriptedModel(tool_call(EXPERTS_CALL), final("**alice** [2]."))
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm] = lambda: client_for(model, tmp_path)
    http = TestClient(app)
    try:
        ok = http.post("/api/ask", json={"org": org, "question": "Who knows falkordb-py?"})
        assert ok.status_code == 200, ok.text
        body = ok.json()
        assert body["answer"] == "**alice** [1]." and body["citations"] == [
            {"n": 1, "node_id": "Person:alice"}
        ]
        assert body["tool_calls"][0]["tool"] == "experts_for" and body["evidence"]["nodes"]

        assert http.post("/api/ask", json={"org": org, "question": ""}).status_code == 422
        assert http.post("/api/ask", json={"org": "bad org!", "question": "x"}).status_code == 422

        app.dependency_overrides[get_llm] = lambda: client_for(
            model, tmp_path / "spent", budget=0.0
        )
        broke = http.post("/api/ask", json={"org": org, "question": "Again?"})
        assert broke.status_code == 503 and "budget" in broke.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        graph.delete()
