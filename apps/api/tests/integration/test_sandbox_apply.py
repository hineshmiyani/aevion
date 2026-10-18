"""Sandbox triage end to end against a mock GitHub: webhook in, label and comment out.

The FalkorDB "brain" is the fixture graph (falkordb-py data); the sandbox graph is a fresh one.
A copied issue is triaged in its original's repo, so its Component comes from falkordb-py.
"""

import hashlib
import hmac
import json
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from falkordb import FalkorDB
from fastapi.testclient import TestClient

from aevion.api.main import app, get_db
from aevion.api.routes import webhooks
from aevion.api.routes.ask import get_llm
from aevion.api.routes.webhooks import get_writer
from aevion.graph.client import OrgGraph
from aevion.graph.naming import graph_name_for
from aevion.graph.schema import bootstrap
from aevion.llm.client import Ledger, LLMClient
from aevion.sandbox.apply import last_run, triage_sandbox_issue
from aevion.sandbox.writer import SandboxWriter
from tests.integration.conftest import load_fixture_pages

pytestmark = pytest.mark.integration

SANDBOX = "hineshmiyani/aevion-sandbox"
REPOSITORY = {"full_name": SANDBOX, "html_url": f"https://github.com/{SANDBOX}"}
SECRET = "test-secret"


class FakeGitHub:
    """Records every request; answers like the GitHub REST API would."""

    def __init__(self) -> None:
        self.requests: list[tuple[str, str, Any]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        self.requests.append((request.method, request.url.path, body))
        path = request.url.path
        if "/collaborators/" in path:
            return httpx.Response(404)  # FalkorDB people aren't sandbox collaborators
        if request.method == "GET" and "/labels/" in path:
            return httpx.Response(404)
        if path.endswith("/comments"):
            return httpx.Response(201, json={"body": body["body"], "html_url": "c-url"})
        return httpx.Response(200 if request.method == "GET" else 201, json={})

    def writes(self) -> list[tuple[str, str, Any]]:
        return [r for r in self.requests if r[0] != "GET"]


def issue_payload(number: int, title: str, body: str) -> dict[str, Any]:
    return {
        "number": number,
        "title": title,
        "body": body,
        "state": "open",
        "html_url": f"https://github.com/{SANDBOX}/issues/{number}",
        "created_at": "2026-10-17T10:00:00Z",
        "user": {"login": "hineshmiyani", "type": "User"},
        "labels": [],
        "assignees": [],
    }


COPY = issue_payload(
    7,
    "Async query timeouts are ignored",
    "Copy for the demo.\n\n<!-- aevion-copy-of: FalkorDB/falkordb-py issue 95 -->",
)


@pytest.fixture
def graphs(
    db: FalkorDB, pr_page: dict[str, Any], issue_page: dict[str, Any]
) -> Iterator[tuple[OrgGraph, OrgGraph]]:
    brain = OrgGraph(db, graph_name_for(f"aevion-test-{uuid.uuid4().hex[:8]}"))
    sandbox = OrgGraph(db, graph_name_for(f"aevion-test-{uuid.uuid4().hex[:8]}"))
    bootstrap(brain)
    bootstrap(sandbox)
    load_fixture_pages(brain, pr_page, issue_page)
    yield brain, sandbox
    brain.delete()
    sandbox.delete()


def _writer(github: FakeGitHub) -> SandboxWriter:
    return SandboxWriter(
        "t", SANDBOX, frozenset({SANDBOX}), transport=httpx.MockTransport(github), pause_s=0
    )


def _llm(tmp_path: Path, reply: str) -> LLMClient:
    def openrouter(request: httpx.Request) -> httpx.Response:
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


def test_writer_refuses_the_real_github_under_test() -> None:
    from aevion.sandbox.writer import WriteNotAllowedError

    with pytest.raises(WriteNotAllowedError):
        SandboxWriter("real-looking-token", SANDBOX, frozenset({SANDBOX}))


def test_copied_issue_is_labelled_named_and_answered_once(
    graphs: tuple[OrgGraph, OrgGraph], tmp_path: Path
) -> None:
    brain, sandbox = graphs
    github = FakeGitHub()
    reply = "Thanks! Likely FalkorDB/falkordb-py#90, fixed in #101. @alice may help."
    run = triage_sandbox_issue(
        brain,
        sandbox,
        _writer(github),
        REPOSITORY,
        COPY,
        client=_llm(tmp_path, reply),
        model="m",
        default_repo="FalkorDB/FalkorDB",
    )
    assert run.issue["context_repo"] == "FalkorDB/falkordb-py"
    assert {a.type: a.status for a in run.actions} == {
        "label": "done",
        "assign_or_mention": "done",
        "comment": "done",
    }
    writes = github.writes()
    assert (
        "POST",
        f"/repos/{SANDBOX}/labels",
        {"name": "area: falkordb", "color": "8a560f", "description": "Suggested by Aevion triage"},
    ) in writes
    assert ("POST", f"/repos/{SANDBOX}/issues/7/labels", {"labels": ["area: falkordb"]}) in writes
    assert not any(p.endswith("/assignees") for _, p, _ in writes)  # alice isn't a collaborator
    (comment,) = [b["body"] for _, p, b in writes if p.endswith("/issues/7/comments")]
    assert "@alice" not in comment and "[alice](https://github.com/alice)" in comment
    assert "`FalkorDB/falkordb-py#90`" in comment and "](https://github.com/FalkorDB" not in comment
    assert all(p.startswith(f"/repos/{SANDBOX}/") for _, p, _ in github.requests)

    stored = last_run(sandbox, f"{SANDBOX}#7")
    assert stored and stored.actions[-1].status == "done"
    again = triage_sandbox_issue(
        brain,
        sandbox,
        _writer(github),
        REPOSITORY,
        COPY,
        client=_llm(tmp_path, reply),
        model="m",
        default_repo="FalkorDB/FalkorDB",
    )
    assert len(github.writes()) == len(writes) and again.actions == run.actions  # no 2nd comment


def _signed(payload: dict[str, Any], event: str, secret: str = SECRET) -> dict[str, Any]:
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    headers = {
        "X-GitHub-Event": event,
        "X-Hub-Signature-256": signature,
        "Content-Type": "application/json",
    }
    return {"content": body, "headers": headers}


def test_webhook(
    db: FalkorDB,
    graphs: tuple[OrgGraph, OrgGraph],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    brain, sandbox = graphs
    github = FakeGitHub()
    settings = webhooks._settings().model_copy(update={"github_webhook_secret": SECRET})
    monkeypatch.setattr(webhooks, "_settings", lambda: settings)
    monkeypatch.setattr(webhooks, "BRAIN_ORG", brain.name.removeprefix("org:"))
    monkeypatch.setattr(webhooks, "SANDBOX_ORG", sandbox.name.removeprefix("org:"))
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm] = lambda: _llm(tmp_path, "Thanks for the report.")
    app.dependency_overrides[get_writer] = lambda: _writer(github)
    http = TestClient(app)
    try:
        opened = {"action": "opened", "issue": COPY, "repository": REPOSITORY}
        bad = _signed(opened, "issues", secret="wrong")
        assert http.post("/webhooks/github", **bad).status_code == 401
        assert http.post("/webhooks/github", **_signed({"zen": "hi"}, "ping")).json() == {
            "status": "pong"
        }
        elsewhere = {**opened, "repository": {"full_name": "FalkorDB/FalkorDB"}}
        ignored = http.post("/webhooks/github", **_signed(elsewhere, "issues"))
        assert ignored.status_code == 202 and "ignored" in ignored.json()["status"]
        assert github.writes() == []

        accepted = http.post("/webhooks/github", **_signed(opened, "issues"))
        assert accepted.status_code == 202, accepted.text
        # TestClient runs background tasks before returning: the triage has happened.
        assert any(p.endswith("/issues/7/comments") for _, p, _ in github.writes())

        comment = {
            "action": "created",
            "issue": COPY,
            "repository": REPOSITORY,
            "comment": {
                "id": 55,
                "body": "thanks!",
                "html_url": "u55",
                "created_at": "2026-10-17T11:00:00Z",
                "user": {"login": "carol", "type": "User"},
            },
        }
        writes_before = len(github.writes())
        assert http.post("/webhooks/github", **_signed(comment, "issue_comment")).status_code == 202
        assert len(github.writes()) == writes_before  # comments are ingested, never triaged
        rows = sandbox.ro_query(
            "MATCH (c:Comment {id: 'ic:55'})-[:ON]->(i:Issue) RETURN i.key"
        ).rows
        assert rows == [[f"{SANDBOX}#7"]]
    finally:
        app.dependency_overrides.clear()


def test_a_fresh_issue_is_placed_by_hints_and_similar_issues(
    graphs: tuple[OrgGraph, OrgGraph], tmp_path: Path
) -> None:
    brain, sandbox = graphs
    fresh = issue_payload(8, "Python client never times out", "The asyncio client hangs.")
    run = triage_sandbox_issue(
        brain,
        sandbox,
        _writer(FakeGitHub()),
        REPOSITORY,
        fresh,
        client=None,
        model=None,
        default_repo="FalkorDB/FalkorDB",
        repo_hints={"FalkorDB/falkordb-py": ("python", "asyncio")},
    )
    assert run.issue["context_repo"] == "FalkorDB/falkordb-py"
    assert "mentions python, asyncio" in run.issue["context_reason"][0]
    assert run.component and run.component["key"] == "FalkorDB/falkordb-py:falkordb"


def test_org_config_hints() -> None:
    from aevion.config import REPO_ROOT
    from aevion.ingest.org_config import load_org_config

    hints = load_org_config(REPO_ROOT / "config/orgs/falkordb.toml").triage_hints()
    assert "python" in hints["FalkorDB/falkordb-py"] and "FalkorDB/FalkorDB" not in hints
