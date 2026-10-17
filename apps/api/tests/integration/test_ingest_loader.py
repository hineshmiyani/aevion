"""Loading normalised pull requests: correct graph shape and idempotent re-runs."""

from collections.abc import Callable
from typing import Any

import pytest

from aevion.graph.client import OrgGraph
from aevion.graph.schema import bootstrap
from aevion.ingest.loader import graph_counts, load_batch, upsert_repo
from aevion.ingest.normalize import Batch, pull_request_from

pytestmark = pytest.mark.integration


def _load(graph: OrgGraph, page: dict[str, Any]) -> None:
    repo = upsert_repo(graph, page)
    batch = Batch()
    for node in page["pullRequests"]["nodes"]:
        pull_request_from(node, repo, 1, frozenset({"dependabot"}), batch)
    load_batch(graph, batch)


def test_second_load_adds_nothing(
    make_graph: Callable[[], OrgGraph], pr_page: dict[str, Any]
) -> None:
    graph = make_graph()
    bootstrap(graph)
    _load(graph, pr_page)
    first = graph_counts(graph)
    _load(graph, pr_page)
    assert graph_counts(graph) == first
    assert first["nodes"] > 0


def test_graph_shape(make_graph: Callable[[], OrgGraph], pr_page: dict[str, Any]) -> None:
    graph = make_graph()
    bootstrap(graph)
    _load(graph, pr_page)

    def one(cypher: str) -> Any:
        return graph.ro_query(cypher).rows[0][0]

    assert one("MATCH (pr:PullRequest) RETURN count(pr)") == 3
    assert one("MATCH (:Person {login: 'alice'})-[:AUTHORED]->(pr) RETURN pr.number") == 101
    assert one("MATCH (:Person {login: 'bob'})-[r:REVIEWED]->() RETURN r.state") == "APPROVED"
    # alice reviewed her own PR: no REVIEWED edge for self-reviews
    assert one("MATCH (:Person {login: 'alice'})-[r:REVIEWED]->() RETURN count(r)") == 0
    assert (
        one(
            "MATCH (:PullRequest {number: 101})-[:MODIFIES]->(:File)-[:IN_COMPONENT]->(c) "
            "RETURN count(DISTINCT c)"
        )
        == 3
    )
    assert one("MATCH (f:File {path: 'README.md'}) RETURN f.is_doc") is True
    assert one("MATCH (c:Component)-[:IN_REPO]->(r:Repo) RETURN count(DISTINCT r)") == 1
