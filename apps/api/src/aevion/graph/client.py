"""FalkorDB access: one `OrgGraph` per GitHub organisation (ADR-0011).

Tools and the text-to-Cypher fallback must read through `ro_query`, which runs
`GRAPH.RO_QUERY` so the database itself refuses any write.
"""

from dataclasses import dataclass
from typing import Any

from falkordb import FalkorDB
from redis.exceptions import ResponseError

from aevion.config import Settings

Params = dict[str, Any]


class ReadOnlyQueryError(Exception):
    """A write was attempted through the read-only query path."""


class GraphNotFoundError(Exception):
    """The graph doesn't exist yet. Run `bootstrap()` for the org before reading."""


# FalkorDB answers GRAPH.RO_QUERY on a missing key with this error; GRAPH.QUERY creates the key.
_MISSING_GRAPH = "empty key"


@dataclass(frozen=True)
class QueryResult:
    columns: list[str]
    rows: list[list[Any]]


def connect(settings: Settings) -> FalkorDB:
    return FalkorDB.from_url(settings.falkordb_url)


class OrgGraph:
    def __init__(self, db: FalkorDB, name: str) -> None:
        self.name = name
        self._graph = db.select_graph(name)

    def query(self, cypher: str, params: Params | None = None) -> QueryResult:
        return _to_result(self._graph.query(cypher, params))

    def ro_query(self, cypher: str, params: Params | None = None) -> QueryResult:
        try:
            return _to_result(self._graph.ro_query(cypher, params))
        except ResponseError as exc:
            message = str(exc).lower()
            if "read-only" in message:
                raise ReadOnlyQueryError(str(exc)) from exc
            if _MISSING_GRAPH in message:
                raise GraphNotFoundError(self.name) from exc
            raise

    def ensure_exists(self) -> None:
        """Create the graph if it's missing. A read-write no-op query is enough."""
        self._graph.query("RETURN 1")

    def delete(self) -> None:
        """Drop the whole graph. A graph that was never written to doesn't exist yet."""
        try:
            self._graph.delete()
        except ResponseError as exc:
            if _MISSING_GRAPH not in str(exc).lower():
                raise


def _to_result(raw: Any) -> QueryResult:
    columns = [
        column[1] if isinstance(column, list | tuple) else str(column) for column in raw.header
    ]
    return QueryResult(columns=columns, rows=[list(row) for row in raw.result_set])
