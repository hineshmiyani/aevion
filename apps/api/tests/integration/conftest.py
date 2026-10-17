"""Fixtures for tests that need a real FalkorDB (run with `pytest -m integration`)."""

import uuid
from collections.abc import Callable, Iterator

import pytest
from falkordb import FalkorDB

from aevion.config import Settings
from aevion.graph.client import OrgGraph, connect


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
