"""GET /api/stats: how big the org graph is, for the first screen ("20,961 nodes …").

Counted live from FalkorDB and kept for a minute, so the numbers are real without every page
view counting the graph.
"""

import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from aevion.api.deps import get_db
from aevion.graph.client import GraphNotFoundError, OrgGraph
from aevion.graph.naming import graph_name_for

router = APIRouter(prefix="/api", tags=["stats"])

TTL_S = 60.0
COUNT_LABELS = """
MATCH (n)
RETURN labels(n)[0] AS label, count(n) AS n
"""
COUNT_EDGES = "MATCH ()-[r]->() RETURN count(r) AS n"


class GraphStats(BaseModel):
    org: str
    nodes: int
    edges: int
    repos: int
    people: int
    pull_requests: int
    issues: int
    decisions: int
    components: int


_cache: dict[str, tuple[float, GraphStats]] = {}


def graph_stats(graph: OrgGraph, org: str) -> GraphStats:
    by_label = {label: n for label, n in graph.ro_query(COUNT_LABELS).rows}
    edges = graph.ro_query(COUNT_EDGES).rows[0][0]
    return GraphStats(
        org=org,
        nodes=sum(by_label.values()),
        edges=edges,
        repos=by_label.get("Repo", 0),
        people=by_label.get("Person", 0),
        pull_requests=by_label.get("PullRequest", 0),
        issues=by_label.get("Issue", 0),
        decisions=by_label.get("Decision", 0),
        components=by_label.get("Component", 0),
    )


@router.get("/stats", response_model=GraphStats)
def stats_route(
    db: Annotated[Any, Depends(get_db)],
    org: Annotated[str, Query(min_length=1, max_length=39)] = "FalkorDB",
) -> GraphStats:
    cached = _cache.get(org.lower())
    if cached and time.monotonic() - cached[0] < TTL_S:
        return cached[1]
    try:
        graph = OrgGraph(db, graph_name_for(org))
        stats = graph_stats(graph, org)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except GraphNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"No graph for org {org!r}") from exc
    _cache[org.lower()] = (time.monotonic(), stats)
    return stats
