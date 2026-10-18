"""Cached answers for the hero questions, stored in the org graph (SPEC OQ-6, AEV-35).

FalkorDB stays the only datastore: each cached answer is a `(:CachedAnswer)` node holding the
full /api/ask response, with a CITES edge to every node its citations point at. So the graph
can say which cached answers lean on a given PR or person, and `aevion warm-cache --refresh`
rebuilds them after a re-ingest.

Only questions warmed on purpose are cached. Everything else is answered live, so a visitor's
own question always reflects the graph as it is.
"""

import hashlib
import re
import time
from collections import defaultdict

from aevion.agent.loop import AskResponse
from aevion.graph.client import OrgGraph
from aevion.tools.evidence import key_property

LOOKUP = """
MATCH (a:CachedAnswer {key: $key})
RETURN a.response AS response
"""

STORE = """
MERGE (a:CachedAnswer {key: $key})
SET a.question = $question, a.response = $response, a.model = $model, a.created_at = $at
WITH a
OPTIONAL MATCH (a)-[old:CITES]->()
DELETE old
"""

# One statement per label, since a label can't be a parameter.
_CITES = """
MATCH (a:CachedAnswer {{key: $key}})
UNWIND $keys AS node_key
MATCH (n:{label} {{{prop}: node_key}})
MERGE (a)-[:CITES]->(n)
"""


def question_key(question: str) -> str:
    """Same question, same key: case, spacing and a trailing '?' don't matter."""
    normal = re.sub(r"\s+", " ", question.lower()).strip().rstrip("?.! ")
    return hashlib.sha256(normal.encode()).hexdigest()[:16]


def cached_answer(graph: OrgGraph, question: str) -> AskResponse | None:
    rows = graph.ro_query(LOOKUP, {"key": question_key(question)}).rows
    if not rows or not rows[0][0]:
        return None
    response = AskResponse.model_validate_json(rows[0][0])
    response.cached = True
    return response


def store_answer(graph: OrgGraph, question: str, response: AskResponse) -> None:
    key = question_key(question)
    stored = response.model_copy(update={"cached": False})
    graph.query(
        STORE,
        {
            "key": key,
            "question": question,
            "response": stored.model_dump_json(),
            "model": response.model,
            "at": int(time.time() * 1000),
        },
    )
    by_label: dict[str, list[str]] = defaultdict(list)
    for citation in response.citations:
        label, node_key = citation.node_id.split(":", 1)
        by_label[label].append(node_key)
    for label, keys in by_label.items():
        if not re.fullmatch(r"[A-Za-z]+", label):
            continue  # labels come from our own tools, but never splice anything else into Cypher
        graph.query(
            _CITES.format(label=label, prop=key_property(label)), {"key": key, "keys": keys}
        )
