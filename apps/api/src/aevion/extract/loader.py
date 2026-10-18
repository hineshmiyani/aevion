"""Write validated Decisions into the org graph. MERGE on the content-derived id, so
re-running extraction (served from the LLM cache) changes nothing."""

from aevion.extract.extractor import DecisionRec, as_rows
from aevion.graph.client import OrgGraph

_UPSERT_DECISIONS = """
UNWIND $rows AS row
MATCH (t:{label} {{key: row.thread_key}})
MERGE (d:Decision {{id: row.id}})
SET d.summary = row.summary, d.rationale = row.rationale, d.alternatives = row.alternatives,
    d.decided_at = row.decided_at, d.confidence = row.confidence, d.model = row.model,
    d.source_url = row.source_url
MERGE (d)-[:DECIDED_IN]->(t)
"""

UPSERT_MADE_BY = """
UNWIND $rows AS row
MATCH (d:Decision {id: row.id}), (p:Person {login: row.login})
MERGE (d)-[:MADE_BY]->(p)
"""

UPSERT_AFFECTS = """
UNWIND $rows AS row
MATCH (d:Decision {id: row.id}), (c:Component {key: row.component})
MERGE (d)-[:AFFECTS]->(c)
"""

UPSERT_EVIDENCE = """
UNWIND $rows AS row
MATCH (d:Decision {id: row.id}), (c:Comment {id: row.comment})
MERGE (d)-[:EVIDENCED_BY]->(c)
"""


# A newer decision supersedes an older one when both affect the same Component and the newer
# decision's thread explicitly links to the older one's (REFERENCES or FIXES, either direction
# through an issue). Evidence-based and deterministic: no LLM call, nothing guessed.
LINK_SUPERSEDES = """
MATCH (new:Decision)-[:DECIDED_IN]->(nt), (old:Decision)-[:DECIDED_IN]->(ot)
WHERE new <> old AND new.decided_at > old.decided_at AND nt <> ot
MATCH (new)-[:AFFECTS]->(c:Component)<-[:AFFECTS]-(old)
MATCH (nt)-[:REFERENCES|FIXES*1..2]-(ot)
WITH DISTINCT new, old
MERGE (new)-[s:SUPERSEDES]->(old)
SET s.at = new.decided_at
"""


def link_supersedes(graph: OrgGraph) -> None:
    graph.query(LINK_SUPERSEDES)


def load_decisions(graph: OrgGraph, decisions: list[DecisionRec]) -> None:
    if not decisions:
        return
    for label in ("PullRequest", "Issue"):
        rows = [r for r in as_rows(decisions) if r["thread_label"] == label]
        if rows:
            graph.query(_UPSERT_DECISIONS.format(label=label), {"rows": rows})
    for query, field, column in (
        (UPSERT_MADE_BY, "made_by", "login"),
        (UPSERT_AFFECTS, "components", "component"),
        (UPSERT_EVIDENCE, "evidence", "comment"),
    ):
        rows = [{"id": d.id, column: value} for d in decisions for value in getattr(d, field)]
        if rows:
            graph.query(query, {"rows": rows})
