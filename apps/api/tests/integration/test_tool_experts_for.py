"""experts_for on the recorded falkordb-py fixture graph, plus its HTTP endpoint."""

import uuid
from typing import Any

import pytest
from falkordb import FalkorDB
from fastapi.testclient import TestClient

from aevion.api.main import app, get_db
from aevion.graph.client import OrgGraph
from aevion.graph.naming import graph_name_for
from aevion.graph.schema import bootstrap
from aevion.tools.evidence import missing_edges
from aevion.tools.experts import ExpertsForArgs, experts_for
from tests.integration.conftest import load_fixture_pages

pytestmark = pytest.mark.integration

COMPONENT = "FalkorDB/falkordb-py:falkordb"


def _logins(rows: list[dict[str, Any]]) -> list[str]:
    return [row["login"] for row in rows]


def test_author_outranks_reviewer_and_bots_are_excluded(fixture_graph: OrgGraph) -> None:
    result = experts_for(fixture_graph, ExpertsForArgs(component=COMPONENT))
    # alice authored merged PR 101 (3 pts); bob reviewed it (2) and left a review comment;
    # carol only commented; the coderabbitai bot reviewed but must never appear.
    assert _logins(result.rows) == ["alice", "bob", "carol"]
    alice, bob, _carol = result.rows
    assert alice["authored_prs"] == 1 and bob["reviewed_prs"] == 1
    assert alice["evidence"][0]["pr"] == "FalkorDB/falkordb-py#101"


def test_open_and_unmerged_prs_do_not_count(fixture_graph: OrgGraph) -> None:
    # PR 103 (docs/, closed without merging) is the only PR touching the docs component
    result = experts_for(fixture_graph, ExpertsForArgs(component="FalkorDB/falkordb-py:docs"))
    assert result.rows == []


def test_path_fragment_finds_component(fixture_graph: OrgGraph) -> None:
    result = experts_for(
        fixture_graph, ExpertsForArgs(component="FALKORDB", repo="FalkorDB/falkordb-py")
    )
    assert _logins(result.rows)[:1] == ["alice"]


def test_every_evidence_edge_exists_in_the_graph(fixture_graph: OrgGraph) -> None:
    result = experts_for(fixture_graph, ExpertsForArgs(component=COMPONENT))
    assert result.evidence.edges, "expected an evidence path"
    assert missing_edges(fixture_graph, result.evidence) == []
    types = {edge.type for edge in result.evidence.edges}
    assert types == {"AUTHORED", "REVIEWED", "MODIFIES", "IN_COMPONENT"}


def test_unknown_component_returns_nothing(fixture_graph: OrgGraph) -> None:
    result = experts_for(fixture_graph, ExpertsForArgs(component="no-such-thing"))
    assert result.rows == [] and result.evidence.nodes == []


def test_http_endpoint(db: FalkorDB, pr_page: dict[str, Any], issue_page: dict[str, Any]) -> None:
    org = f"aevion-test-{uuid.uuid4().hex[:8]}"
    graph = OrgGraph(db, graph_name_for(org))
    bootstrap(graph)
    load_fixture_pages(graph, pr_page, issue_page)
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)
    try:
        ok = client.post(
            "/api/tools/experts_for", json={"org": org.upper(), "component": COMPONENT}
        )
        assert ok.status_code == 200
        body = ok.json()
        assert [row["login"] for row in body["rows"]] == ["alice", "bob", "carol"]
        assert body["evidence"]["edges"] and body["cypher"]

        assert (
            client.post(
                "/api/tools/experts_for", json={"org": "no-such-org", "component": "x"}
            ).status_code
            == 404
        )
        assert client.post("/api/tools/nope", json={"org": org}).status_code == 404
        assert (
            client.post("/api/tools/experts_for", json={"component": COMPONENT}).status_code == 422
        )
        assert (
            client.post(
                "/api/tools/experts_for", json={"org": "bad org!", "component": "x"}
            ).status_code
            == 422
        )
        assert client.get("/api/tools").json()[0]["name"] == "experts_for"
    finally:
        app.dependency_overrides.clear()
        graph.delete()
