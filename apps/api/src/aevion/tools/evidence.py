"""Evidence paths: the graph nodes and edges behind every tool answer (GLOSSARY: Evidence path).

Node ids are `<Label>:<key>`, using each label's MERGE key, so any edge in an EvidencePath
can be checked against the graph with `missing_edges()` (SPEC success criterion 2).
"""

from typing import Any

from pydantic import BaseModel, Field

from aevion.graph.client import OrgGraph

# The MERGE key property for each node label (docs/architecture/graph-model.md).
KEY_PROPERTY = {"Person": "login", "Repo": "full_name", "Comment": "id", "Decision": "id"}


def key_property(label: str) -> str:
    return KEY_PROPERTY.get(label, "key")


def node_id(label: str, key: str) -> str:
    return f"{label}:{key}"


class EvidenceNode(BaseModel):
    id: str
    label: str
    title: str
    url: str | None = None


class EvidenceEdge(BaseModel):
    source: str
    target: str
    type: str


class EvidencePath(BaseModel):
    nodes: list[EvidenceNode] = Field(default_factory=list)
    edges: list[EvidenceEdge] = Field(default_factory=list)


class EvidenceBuilder:
    """Collects nodes and edges once each, in insertion order."""

    def __init__(self) -> None:
        self._nodes: dict[str, EvidenceNode] = {}
        self._edges: dict[tuple[str, str, str], EvidenceEdge] = {}

    def node(self, label: str, key: str, title: str | None = None, url: str | None = None) -> str:
        nid = node_id(label, key)
        if nid not in self._nodes:
            self._nodes[nid] = EvidenceNode(id=nid, label=label, title=title or key, url=url)
        return nid

    def edge(self, source: str, edge_type: str, target: str) -> None:
        self._edges.setdefault(
            (source, edge_type, target), EvidenceEdge(source=source, target=target, type=edge_type)
        )

    def build(self) -> EvidencePath:
        return EvidencePath(nodes=list(self._nodes.values()), edges=list(self._edges.values()))


class ToolResult(BaseModel):
    """What every Cypher tool returns: rows for the agent, evidence and Cypher for the user."""

    tool: str
    args: dict[str, Any]
    rows: list[dict[str, Any]]
    evidence: EvidencePath
    cypher: list[str]


def missing_edges(graph: OrgGraph, evidence: EvidencePath) -> list[EvidenceEdge]:
    """Edges in `evidence` that don't exist in the graph. An honest tool returns []."""
    missing: list[EvidenceEdge] = []
    for edge in evidence.edges:
        source_label, source_key = edge.source.split(":", 1)
        target_label, target_key = edge.target.split(":", 1)
        cypher = (
            f"MATCH (a:{source_label} {{{key_property(source_label)}: $a}})"
            f"-[r:{edge.type}]->(b:{target_label} {{{key_property(target_label)}: $b}}) "
            "RETURN count(r)"
        )
        if graph.ro_query(cypher, {"a": source_key, "b": target_key}).rows[0][0] == 0:
            missing.append(edge)
    return missing
