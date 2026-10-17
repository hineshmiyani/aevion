"""Triage dry runs on the fixture graph, with the model scripted (no network, no key spent)."""

import json
import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest
from falkordb import FalkorDB
from fastapi.testclient import TestClient

from aevion.api.main import app, get_db
from aevion.api.routes.ask import get_llm
from aevion.graph.client import OrgGraph
from aevion.graph.naming import graph_name_for
from aevion.graph.schema import bootstrap
from aevion.llm.client import Ledger, LLMClient
from aevion.triage.service import (
    ApplyNotAllowedError,
    check_mode,
    defuse_mentions,
    resolve_bare_refs,
    triage,
)
from tests.integration.conftest import load_fixture_pages

pytestmark = pytest.mark.integration

REPO = "FalkorDB/falkordb-py"
SANDBOX = frozenset({"hineshmiyani/aevion-sandbox"})


def _client(tmp_path: Path, reply: str, requests: list[dict[str, Any]]) -> LLMClient:
    def openrouter(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        body = {"choices": [{"message": {"content": reply}}], "usage": {"cost": 0.0001}}
        return httpx.Response(200, json=body)

    return LLMClient(
        "sk-or-test",
        base_url="https://openrouter.test/api/v1",
        cache_dir=None,
        ledger=Ledger(tmp_path / "ledger.jsonl"),
        budget_usd=1.0,
        transport=httpx.MockTransport(openrouter),
    )


def test_mentions_are_defused_but_code_and_emails_are_left_alone() -> None:
    text = "Ask @alice, not `@bob` or bob@example.com."
    assert defuse_mentions(text) == (
        "Ask [alice](https://github.com/alice), not `@bob` or bob@example.com."
    )


def test_bare_refs_link_to_the_item_meant_or_stop_linking() -> None:
    known = [{"key": "FalkorDB/FalkorDB#90", "url": "u90", "fixed_by": ["FalkorDB/FalkorDB#101"]}]
    text = resolve_bare_refs(
        "See #90, fixed by #101; also #7 and [x#5](y).", "FalkorDB/FalkorDB#1", known
    )
    assert text == (
        "See [FalkorDB/FalkorDB#90](u90), fixed by "
        "[FalkorDB/FalkorDB#101](https://github.com/FalkorDB/FalkorDB/pull/101); "
        "also \\#7 and [x#5](y)."
    )


def test_apply_outside_the_allow_list_fails_before_any_work() -> None:
    with pytest.raises(ApplyNotAllowedError):
        check_mode("FalkorDB/FalkorDB#1", "apply", SANDBOX)
    check_mode("FalkorDB/FalkorDB#1", "dry_run", SANDBOX)  # dry runs work anywhere
    check_mode("hineshmiyani/aevion-sandbox#1", "apply", SANDBOX)


def test_dry_run_with_a_model_reply(fixture_graph: OrgGraph, tmp_path: Path) -> None:
    requests: list[dict[str, Any]] = []
    client = _client(tmp_path, "Thanks! See #90. @alice may be able to help.", requests)
    response = triage(
        fixture_graph, f"{REPO}#95", "dry_run", allowed_repos=SANDBOX, client=client, model="m"
    )
    assert response.component and response.component["key"] == f"{REPO}:falkordb"
    assert response.expert and response.expert["login"] in {"alice", "bob"}
    assert "@alice" not in response.draft_reply  # the model's mention was defused
    assert "[alice](https://github.com/alice)" in response.draft_reply
    assert [a.type for a in response.actions][-1] == "comment"
    assert all(a.status in {"proposed", "skipped"} for a in response.actions)
    facts = json.loads(requests[0]["messages"][1]["content"])
    assert facts["related"][0]["key"] == f"{REPO}#90" or facts["likely_duplicates"]


def test_dry_run_falls_back_to_the_template(fixture_graph: OrgGraph) -> None:
    response = triage(fixture_graph, f"{REPO}#95", "dry_run", allowed_repos=SANDBOX)
    assert response.model is None
    assert f"[{REPO}#90]" in response.draft_reply and "fixed by" in response.draft_reply
    assert "`falkordb`" in response.draft_reply and "@" not in response.draft_reply


def test_triage_endpoint(
    db: FalkorDB, pr_page: dict[str, Any], issue_page: dict[str, Any], tmp_path: Path
) -> None:
    org = f"aevion-test-{uuid.uuid4().hex[:8]}"
    graph = OrgGraph(db, graph_name_for(org))
    bootstrap(graph)
    load_fixture_pages(graph, pr_page, issue_page)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm] = lambda: _client(tmp_path, "Thanks for the report.", [])
    http = TestClient(app)
    try:
        ok = http.post("/api/triage", json={"org": org, "issue_key": f"{REPO}#95"})
        assert ok.status_code == 200, ok.text
        body = ok.json()
        assert body["mode"] == "dry_run" and body["evidence"]["nodes"] and body["cypher"]

        real_repo_apply = {"org": org, "issue_key": f"{REPO}#95", "mode": "apply"}
        assert http.post("/api/triage", json=real_repo_apply).status_code == 403
        sandbox_apply = {"org": org, "issue_key": "hineshmiyani/aevion-sandbox#1", "mode": "apply"}
        assert http.post("/api/triage", json=sandbox_apply).status_code == 501
        missing = {"org": org, "issue_key": f"{REPO}#4040"}
        assert http.post("/api/triage", json=missing).status_code == 404
        assert http.post("/api/triage", json={"org": org, "issue_key": "nope"}).status_code == 422
    finally:
        app.dependency_overrides.clear()
        graph.delete()
