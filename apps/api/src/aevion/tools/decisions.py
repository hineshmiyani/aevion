"""decision_trail: why was X decided? (US-2)

Finds Decisions by full-text search over their summary and rationale (optionally within a
Component), re-ranks the candidates by how many of the topic's keywords each one covers, then
walks each one's trail: the thread it was decided in, the issues that thread
fixed, the comments that evidence it, the people who made it, the Components it affects, and
any SUPERSEDES chain, so an answer can say what we believed before and what replaced it.
"""

import re
from typing import Any

from pydantic import BaseModel, Field, model_validator

from aevion.graph.client import OrgGraph
from aevion.tools.evidence import EvidenceBuilder, ToolResult
from aevion.tools.scope import as_dicts, iso, resolve_components

_STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "did",
        "do",
        "does",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "this",
        "to",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
    ]
)

# The index finds candidates; it can't rank them well on its own. Its TF-IDF score rewards
# short text that repeats one query word, so "merge queue entries aren't cancelled" outscores
# "gate main with a merge queue" for "why gate main on a merge queue". We fetch a wide pool and
# re-rank in Python by keyword coverage (see _rank).
SEARCH = """
CALL db.idx.fulltext.queryNodes('Decision', $query) YIELD node, score
OPTIONAL MATCH (node)-[:AFFECTS]->(c:Component)
WITH node, score, collect(c.key) AS affects
WHERE size($components) = 0 OR any(k IN affects WHERE k IN $components)
RETURN node.id AS id, score, node.confidence AS confidence,
       node.summary + ' ' + node.rationale AS text
ORDER BY score DESC
LIMIT $pool
"""
SEARCH_POOL = 50

BY_COMPONENT = """
MATCH (d:Decision)-[:AFFECTS]->(c:Component)
WHERE c.key IN $components
WITH DISTINCT d
RETURN d.id AS id, d.decided_at AS decided_at
ORDER BY decided_at DESC
LIMIT $limit
"""

TRAIL = """
MATCH (d:Decision {id: $id})-[:DECIDED_IN]->(t)
OPTIONAL MATCH (t)-[:FIXES]->(fixed:Issue)
OPTIONAL MATCH (d)-[:MADE_BY]->(p:Person)
OPTIONAL MATCH (d)-[:AFFECTS]->(c:Component)
RETURN d.summary AS summary, d.rationale AS rationale, d.alternatives AS alternatives,
       d.decided_at AS decided_at, d.confidence AS confidence,
       labels(t)[0] AS thread_label, t.key AS thread_key, t.title AS thread_title,
       t.url AS thread_url,
       collect(DISTINCT [fixed.key, fixed.title, fixed.url]) AS fixed,
       collect(DISTINCT p.login) AS made_by,
       collect(DISTINCT [c.key, c.name]) AS components
"""

EVIDENCE = """
MATCH (d:Decision {id: $id})-[:EVIDENCED_BY]->(cm:Comment)
OPTIONAL MATCH (a:Person)-[:AUTHORED]->(cm)
RETURN cm.id AS id, cm.excerpt AS excerpt, cm.url AS url, a.login AS author
LIMIT 4
"""

SUPERSEDES = """
MATCH (d:Decision {id: $id})
OPTIONAL MATCH (d)-[:SUPERSEDES]->(older:Decision)
OPTIONAL MATCH (newer:Decision)-[:SUPERSEDES]->(d)
RETURN collect(DISTINCT [older.id, older.summary, older.decided_at]) AS replaces,
       collect(DISTINCT [newer.id, newer.summary, newer.decided_at]) AS replaced_by
"""


class DecisionTrailArgs(BaseModel):
    topic: str | None = Field(
        default=None, description="What the decision was about, e.g. 'merge queue for CI'."
    )
    component: str | None = Field(default=None, description="Component key or path fragment.")
    repo: str | None = Field(default=None, description="Restrict the Component lookup to a repo.")
    limit: int = Field(default=3, ge=1, le=10)

    @model_validator(mode="after")
    def _needs_something(self) -> "DecisionTrailArgs":
        if not (self.topic and self.topic.strip()) and not self.component:
            raise ValueError("give a topic or a component")
        return self


def keywords(topic: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", topic.lower())
    return list(dict.fromkeys(w for w in words if len(w) > 2 and w not in _STOPWORDS))


def fulltext_query(topic: str) -> str | None:
    """User words → a safe full-text OR query. FalkorDB's index stems, so 'queues' finds 'queue'."""
    return "|".join(keywords(topic)) or None


def _stem(word: str) -> str:
    """Crude suffix stripping, enough to agree with the index's stemmer on common forms."""
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def _rank(topic: str, candidates: list[list[Any]], limit: int) -> list[str]:
    """Order by keyword coverage, then text score weighted by the extractor's confidence.

    Coverage is the share of the topic's distinct keywords that appear in the decision, so a
    decision about every part of the question beats one that repeats a single word of it.
    """
    wanted = {_stem(w) for w in keywords(topic)}

    def key(row: list[Any]) -> tuple[float, float]:
        _id, score, confidence, text = row
        present = {_stem(w) for w in re.findall(r"[a-z0-9]+", (text or "").lower())}
        coverage = len(wanted & present) / len(wanted) if wanted else 0.0
        return (-round(coverage, 2), -float(score) * float(confidence or 0))

    return [row[0] for row in sorted(candidates, key=key)[:limit]]


def decision_trail(graph: OrgGraph, args: DecisionTrailArgs) -> ToolResult:
    components = resolve_components(graph, args.component, args.repo) if args.component else []
    keys = [row[0] for row in components]
    query = fulltext_query(args.topic) if args.topic else None
    cypher = [TRAIL.strip(), EVIDENCE.strip(), SUPERSEDES.strip()]

    if query:
        pool = graph.ro_query(SEARCH, {"query": query, "components": keys, "pool": SEARCH_POOL})
        ids = _rank(args.topic or "", pool.rows, args.limit)
        cypher.insert(0, SEARCH.strip())
    elif keys:
        ids = [
            r[0]
            for r in graph.ro_query(BY_COMPONENT, {"components": keys, "limit": args.limit}).rows
        ]
        cypher.insert(0, BY_COMPONENT.strip())
    else:
        ids = []

    evidence = EvidenceBuilder()
    rows: list[dict[str, Any]] = []
    for decision_id in ids:
        trail = as_dicts(graph.ro_query(TRAIL, {"id": decision_id}))[0]
        quotes = as_dicts(graph.ro_query(EVIDENCE, {"id": decision_id}))
        history = as_dicts(graph.ro_query(SUPERSEDES, {"id": decision_id}))[0]
        rows.append(_row(decision_id, trail, quotes, history))
        _add_evidence(evidence, decision_id, trail, quotes, history)

    return ToolResult(
        tool="decision_trail",
        args=args.model_dump(),
        rows=rows,
        evidence=evidence.build(),
        cypher=cypher,
    )


def _row(
    decision_id: str, trail: dict[str, Any], quotes: list[dict[str, Any]], history: dict[str, Any]
) -> dict[str, Any]:
    def pairs(items: list[list[Any]]) -> list[dict[str, Any]]:
        return [{"id": i, "summary": s, "decided": iso(at)} for i, s, at in items if i]

    return {
        "id": decision_id,
        "summary": trail["summary"],
        "rationale": trail["rationale"],
        "alternatives": trail["alternatives"] or [],
        "decided": iso(trail["decided_at"]),
        "confidence": trail["confidence"],
        "decided_in": {
            "key": trail["thread_key"],
            "title": trail["thread_title"],
            "url": trail["thread_url"],
        },
        "fixed_issues": [{"key": k, "title": t, "url": u} for k, t, u in trail["fixed"] if k],
        "made_by": [p for p in trail["made_by"] if p],
        "components": [k for k, _name in trail["components"] if k],
        "quotes": [
            {"author": q["author"], "excerpt": q["excerpt"], "url": q["url"]} for q in quotes
        ],
        "replaces": pairs(history["replaces"]),
        "replaced_by": pairs(history["replaced_by"]),
    }


def _add_evidence(
    evidence: EvidenceBuilder,
    decision_id: str,
    trail: dict[str, Any],
    quotes: list[dict[str, Any]],
    history: dict[str, Any],
) -> None:
    dec = evidence.node("Decision", decision_id, title=trail["summary"])
    thread = evidence.node(
        trail["thread_label"],
        trail["thread_key"],
        title=trail["thread_title"],
        url=trail["thread_url"],
    )
    evidence.edge(dec, "DECIDED_IN", thread)
    for key, title, url in trail["fixed"]:
        if key:
            evidence.edge(thread, "FIXES", evidence.node("Issue", key, title=title, url=url))
    for login in trail["made_by"]:
        if login:
            evidence.edge(
                dec, "MADE_BY", evidence.node("Person", login, url=f"https://github.com/{login}")
            )
    for key, name in trail["components"]:
        if key:
            evidence.edge(dec, "AFFECTS", evidence.node("Component", key, title=name))
    for q in quotes:
        comment = evidence.node(
            "Comment", q["id"], title=f"{q['author']}: {(q['excerpt'] or '')[:80]}", url=q["url"]
        )
        evidence.edge(dec, "EVIDENCED_BY", comment)
    for older_id, summary, _at in history["replaces"]:
        if older_id:
            evidence.edge(dec, "SUPERSEDES", evidence.node("Decision", older_id, title=summary))
    for newer_id, summary, _at in history["replaced_by"]:
        if newer_id:
            evidence.edge(evidence.node("Decision", newer_id, title=summary), "SUPERSEDES", dec)
