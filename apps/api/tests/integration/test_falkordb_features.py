"""Proves the FalkorDB features the design relies on (SPEC assumption 3, AEV-17).

If one of these fails, the fallback is recorded in docs/architecture/graph-model.md
before any tool depends on the feature.
"""

import time
import uuid
from collections.abc import Callable

import pytest
from falkordb import FalkorDB

from aevion.graph.client import GraphNotFoundError, OrgGraph, ReadOnlyQueryError
from aevion.graph.schema import INDEXES, bootstrap

pytestmark = pytest.mark.integration

DAY_MS = 86_400_000


def test_timestamp_returns_epoch_milliseconds(make_graph: Callable[[], OrgGraph]) -> None:
    graph = make_graph()
    before = int(time.time() * 1000)
    (now,) = graph.ro_query("RETURN timestamp() AS now").rows[0]
    after = int(time.time() * 1000)
    assert before - 1000 <= now <= after + 1000


def test_exp_supports_recency_decay(make_graph: Callable[[], OrgGraph]) -> None:
    graph = make_graph()
    (value,) = graph.ro_query("RETURN exp(-260.0 / 260.0) AS v").rows[0]
    assert value == pytest.approx(0.36788, rel=1e-4)


def test_expertise_query_sketch_ranks_recent_authors_higher(
    make_graph: Callable[[], OrgGraph],
) -> None:
    """The query from graph-model.md runs as written and weights recency."""
    graph = make_graph()
    now = int(time.time() * 1000)
    graph.query(
        """
        CREATE (c:Component {key: 'r:src/core'}),
               (f:File {key: 'r:src/core/a.c'})-[:IN_COMPONENT]->(c),
               (recent:PullRequest {key: 'r#1', url: 'u1', merged_at: $recent}),
               (old:PullRequest {key: 'r#2', url: 'u2', merged_at: $old}),
               (recent)-[:MODIFIES]->(f), (old)-[:MODIFIES]->(f),
               (:Person {login: 'alice', is_bot: false})-[:AUTHORED]->(recent),
               (:Person {login: 'bob', is_bot: false})-[:AUTHORED]->(old),
               (:Person {login: 'ci[bot]', is_bot: true})-[:AUTHORED]->(recent)
        """,
        {"recent": now - 10 * DAY_MS, "old": now - 400 * DAY_MS},
    )
    rows = graph.ro_query(
        """
        MATCH (c:Component {key: $component})<-[:IN_COMPONENT]-(:File)<-[:MODIFIES]-(pr:PullRequest)
        WHERE pr.merged_at IS NOT NULL
        MATCH (p:Person)-[r:AUTHORED|REVIEWED]->(pr)
        WHERE NOT p.is_bot
        WITH p, pr,
             CASE type(r) WHEN 'AUTHORED' THEN 3.0 ELSE 2.0 END AS weight,
             (timestamp() - pr.merged_at) / 86400000.0 AS age_days
        WITH p, sum(weight * exp(-age_days / 260.0)) AS score,
             collect(DISTINCT pr.url)[..5] AS evidence
        RETURN p.login AS person, round(score * 10) / 10 AS score, evidence
        ORDER BY score DESC
        LIMIT 5
        """,
        {"component": "r:src/core"},
    ).rows
    assert [row[0] for row in rows] == ["alice", "bob"]  # bot excluded, recent first
    assert rows[0][1] > rows[1][1]
    assert rows[0][2] == ["u1"]


def test_fulltext_index_finds_issues_by_title(make_graph: Callable[[], OrgGraph]) -> None:
    graph = make_graph()
    graph.query("CALL db.idx.fulltext.createNodeIndex('Issue', 'title', 'body_excerpt')")
    graph.query(
        "CREATE (:Issue {key: 'r#1', title: 'Vector index crashes on restart', body_excerpt: ''}),"
        "       (:Issue {key: 'r#2', title: 'Docs typo', body_excerpt: ''})"
    )
    rows = graph.ro_query(
        "CALL db.idx.fulltext.queryNodes('Issue', 'vector') YIELD node RETURN node.key"
    ).rows
    assert rows == [["r#1"]]


def test_graphs_are_isolated(make_graph: Callable[[], OrgGraph]) -> None:
    """One graph per org (ADR-0011): data in one graph is invisible to another."""
    org_a, org_b = make_graph(), make_graph()
    org_a.query("CREATE (:Person {login: 'alice'})")
    assert org_a.ro_query("MATCH (p:Person) RETURN count(p)").rows == [[1]]
    assert org_b.ro_query("MATCH (p:Person) RETURN count(p)").rows == [[0]]


def test_ro_query_rejects_writes(make_graph: Callable[[], OrgGraph]) -> None:
    graph = make_graph()
    with pytest.raises(ReadOnlyQueryError):
        graph.ro_query("CREATE (:Person {login: 'mallory'})")
    assert graph.ro_query("MATCH (n) RETURN count(n)").rows == [[0]]


def test_ro_query_on_missing_graph_raises_clear_error(db: FalkorDB) -> None:
    """Found in AEV-17: GRAPH.RO_QUERY can't create a graph, so reads need bootstrap first."""
    missing = OrgGraph(db, f"test:missing-{uuid.uuid4().hex[:8]}")
    with pytest.raises(GraphNotFoundError):
        missing.ro_query("RETURN 1")


def test_bootstrap_creates_graph_and_is_idempotent(db: FalkorDB) -> None:
    graph = OrgGraph(db, f"test:bootstrap-{uuid.uuid4().hex[:8]}")
    try:
        bootstrap(graph)  # graph doesn't exist yet
        bootstrap(graph)  # second run must not raise
        labels = {
            row[0] for row in graph.ro_query("CALL db.indexes() YIELD label RETURN label").rows
        }
        assert {index.label for index in INDEXES} <= labels
    finally:
        graph.delete()


def test_bootstrap_is_idempotent(make_graph: Callable[[], OrgGraph]) -> None:
    graph = make_graph()
    bootstrap(graph)
    bootstrap(graph)  # second run must not raise
    labels = {row[0] for row in graph.ro_query("CALL db.indexes() YIELD label RETURN label").rows}
    assert {index.label for index in INDEXES} <= labels
