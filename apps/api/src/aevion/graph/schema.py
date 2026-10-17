"""Index bootstrap for an org graph. Mirrors docs/architecture/graph-model.md#indexes."""

from dataclasses import dataclass
from typing import Literal

from aevion.graph.client import OrgGraph


@dataclass(frozen=True)
class Index:
    label: str
    properties: tuple[str, ...]
    kind: Literal["RANGE", "FULLTEXT"] = "RANGE"


INDEXES: tuple[Index, ...] = (
    Index("Repo", ("full_name",)),
    Index("Person", ("login",)),
    Index("Label", ("key",)),
    Index("Team", ("key",)),
    Index("Release", ("key",)),
    Index("Issue", ("key",)),
    Index("PullRequest", ("key",)),
    Index("PullRequest", ("merged_at",)),
    Index("Comment", ("id",)),
    Index("File", ("key",)),
    Index("Component", ("key",)),
    Index("Decision", ("id",)),
    Index("Issue", ("title", "body_excerpt"), "FULLTEXT"),
    Index("Decision", ("summary", "rationale"), "FULLTEXT"),
)


def bootstrap(graph: OrgGraph) -> None:
    """Create the graph and every missing index. Safe to run on every start."""
    graph.ensure_exists()
    existing = _existing_indexes(graph)
    for index in INDEXES:
        missing = [p for p in index.properties if (index.label, p, index.kind) not in existing]
        if not missing:
            continue
        if index.kind == "FULLTEXT":
            args = ", ".join(f"'{p}'" for p in missing)
            graph.query(f"CALL db.idx.fulltext.createNodeIndex('{index.label}', {args})")
        else:
            for prop in missing:
                graph.query(f"CREATE INDEX FOR (n:{index.label}) ON (n.{prop})")


def _existing_indexes(graph: OrgGraph) -> set[tuple[str, str, str]]:
    rows = graph.ro_query("CALL db.indexes() YIELD label, types RETURN label, types").rows
    return {
        (label, prop, kind)
        for label, types in rows
        for prop, kinds in types.items()
        for kind in kinds
    }
