"""Shared helpers for tools that work on a Component (or a whole repo) and a time window."""

from datetime import UTC, datetime, timedelta
from typing import Any

from aevion.graph.client import OrgGraph, QueryResult

DAY_MS = 86_400_000

MATCH_COMPONENTS = """
MATCH (c:Component)
WHERE (c.key = $component OR toLower(c.path_prefix) CONTAINS toLower($component))
  AND ($repo IS NULL OR c.repo = $repo)
RETURN c.key, c.name, c.repo
ORDER BY c.key = $component DESC, size(c.path_prefix)
LIMIT 5
"""


def resolve_components(graph: OrgGraph, component: str, repo: str | None) -> list[list[Any]]:
    """Rows of [key, name, repo] for an exact Component key or a path fragment."""
    return graph.ro_query(MATCH_COMPONENTS, {"component": component, "repo": repo}).rows


def since_ms(days: int | None = None, iso_date: str | None = None) -> int:
    """Window start in epoch ms, from an ISO date ('2026-10-01') or a number of days back."""
    if iso_date:
        start = datetime.fromisoformat(iso_date)
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
    else:
        start = datetime.now(UTC) - timedelta(days=days or 90)
    return int(start.timestamp() * 1000)


def as_dicts(result: QueryResult) -> list[dict[str, Any]]:
    return [dict(zip(result.columns, row, strict=True)) for row in result.rows]


def iso(ms: int | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, UTC).strftime("%Y-%m-%d")
