"""Fixtures for tests that need a real FalkorDB (run with `pytest -m integration`)."""

import uuid
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from falkordb import FalkorDB

from aevion.config import Settings
from aevion.graph.client import OrgGraph, connect
from aevion.graph.schema import bootstrap
from aevion.ingest.loader import link_references, load_batch, upsert_repo
from aevion.ingest.normalize import Batch, issue_from, pull_request_from

FIXTURE_BOTS = frozenset({"dependabot"})


@pytest.fixture(scope="session")
def db() -> FalkorDB:
    try:
        client = connect(Settings())
        client.connection.ping()
    except Exception as exc:  # any connection failure means "not available here"
        pytest.skip(f"FalkorDB not reachable: {exc}")
    return client


@pytest.fixture
def make_graph(db: FalkorDB) -> Iterator[Callable[[], OrgGraph]]:
    """Create throwaway graphs with unique names; delete them after the test.

    Graphs are created up front, as `bootstrap()` does in production, because FalkorDB's
    read-only query fails on a graph that doesn't exist yet.
    """
    created: list[OrgGraph] = []

    def _make() -> OrgGraph:
        graph = OrgGraph(db, f"test:{uuid.uuid4().hex[:12]}")
        graph.ensure_exists()
        created.append(graph)
        return graph

    yield _make
    for graph in created:
        graph.delete()


def load_fixture_pages(
    graph: OrgGraph, pr_page: dict[str, Any], issue_page: dict[str, Any]
) -> None:
    """Load the recorded falkordb-py fixture pages the way the ingestion pipeline does."""
    repo = upsert_repo(graph, pr_page)
    batch = Batch()
    for node in pr_page["pullRequests"]["nodes"]:
        pull_request_from(node, repo, 1, FIXTURE_BOTS, batch)
    load_batch(graph, batch)
    batch = Batch()
    for node in issue_page["issues"]["nodes"]:
        issue_from(node, repo, FIXTURE_BOTS, batch)
    load_batch(graph, batch)
    link_references(graph)


@pytest.fixture
def fixture_graph(
    make_graph: Callable[[], OrgGraph], pr_page: dict[str, Any], issue_page: dict[str, Any]
) -> OrgGraph:
    """A bootstrapped graph holding the recorded falkordb-py fixture data."""
    graph = make_graph()
    bootstrap(graph)
    load_fixture_pages(graph, pr_page, issue_page)
    return graph
