"""Loading normalised pull requests and issues: correct graph shape and idempotent re-runs."""

from typing import Any

import pytest

from aevion.graph.client import OrgGraph
from aevion.ingest.loader import graph_counts
from tests.integration.conftest import load_fixture_pages

pytestmark = pytest.mark.integration


@pytest.fixture
def loaded(fixture_graph: OrgGraph) -> OrgGraph:
    return fixture_graph


def _one(graph: OrgGraph, cypher: str) -> Any:
    return graph.ro_query(cypher).rows[0][0]


def test_second_load_adds_nothing(
    loaded: OrgGraph, pr_page: dict[str, Any], issue_page: dict[str, Any]
) -> None:
    first = graph_counts(loaded)
    load_fixture_pages(loaded, pr_page, issue_page)
    assert graph_counts(loaded) == first
    assert first["nodes"] > 0


def test_pull_request_shape(loaded: OrgGraph) -> None:
    assert _one(loaded, "MATCH (pr:PullRequest) RETURN count(pr)") == 3
    assert (
        _one(
            loaded,
            "MATCH (:Person {login: 'alice'})-[:AUTHORED]->(pr:PullRequest) RETURN pr.number",
        )
        == 101
    )
    assert (
        _one(loaded, "MATCH (:Person {login: 'bob'})-[r:REVIEWED]->() RETURN r.state") == "APPROVED"
    )
    # alice reviewed her own PR: no REVIEWED edge for self-reviews
    assert _one(loaded, "MATCH (:Person {login: 'alice'})-[r:REVIEWED]->() RETURN count(r)") == 0
    assert (
        _one(
            loaded,
            "MATCH (:PullRequest {number: 101})-[:MODIFIES]->(:File)-[:IN_COMPONENT]->(c) "
            "RETURN count(DISTINCT c)",
        )
        == 3
    )
    assert _one(loaded, "MATCH (f:File {path: 'README.md'}) RETURN f.is_doc") is True


def test_issue_shape(loaded: OrgGraph) -> None:
    assert _one(loaded, "MATCH (i:Issue) RETURN count(i)") == 3
    assert _one(loaded, "MATCH (:Issue {number: 90})-[:ASSIGNED_TO]->(p) RETURN p.login") == "alice"
    assert _one(loaded, "MATCH (:Issue {number: 90})-[:HAS_LABEL]->(l) RETURN l.name") == "bug"
    assert (
        _one(loaded, "MATCH (:Person {login: 'carol'})-[:AUTHORED]->(i:Issue) RETURN i.number")
        == 90
    )


def test_fixes_and_references(loaded: OrgGraph) -> None:
    assert _one(loaded, "MATCH (:PullRequest {number: 101})-[:FIXES]->(i) RETURN i.number") == 90
    # PR 101 references issue 95; issue 90 references PR 101; issue 96 references issue 90
    refs = loaded.ro_query(
        "MATCH (s)-[:REFERENCES]->(t) RETURN s.number, t.number ORDER BY s.number, t.number"
    ).rows
    assert refs == [[90, 101], [96, 90], [101, 95]]


def test_comments_link_thread_and_author(loaded: OrgGraph) -> None:
    rows = loaded.ro_query(
        "MATCH (p:Person)-[:AUTHORED]->(c:Comment)-[:ON]->(t) "
        "RETURN c.id, c.kind, p.login, t.number ORDER BY c.id"
    ).rows
    assert rows == [
        ["ic:501", "issue", "carol", 101],
        ["ic:601", "issue", "alice", 90],
        ["rc:21", "review_thread", "bob", 101],
        ["rv:11", "review", "bob", 101],
    ]
