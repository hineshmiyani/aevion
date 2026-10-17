"""related_work: what else does this issue or PR touch? (US-4)

Linked issues and PRs (FIXES / REFERENCES, both directions), the files and Components the
work touches, and other PRs changing the same files: the overlap a maintainer would want
to know about before merging.
"""

from typing import Any

from pydantic import BaseModel, Field

from aevion.graph.client import OrgGraph
from aevion.tools.evidence import EvidenceBuilder, ToolResult
from aevion.tools.scope import as_dicts, iso

FIND_ITEM = """
OPTIONAL MATCH (pr:PullRequest {key: $key})
OPTIONAL MATCH (i:Issue {key: $key})
RETURN CASE WHEN pr IS NOT NULL THEN 'PullRequest' WHEN i IS NOT NULL THEN 'Issue' END AS label,
       coalesce(pr.title, i.title) AS title, coalesce(pr.url, i.url) AS url,
       coalesce(pr.state, i.state) AS state
"""

_LINKS = """
MATCH (n:{label} {{key: $key}})-[r:FIXES|REFERENCES]->(m)
RETURN 'out' AS direction, type(r) AS link, labels(m)[0] AS label, m.key AS key,
       m.title AS title, m.url AS url, m.state AS state
UNION
MATCH (m)-[r:FIXES|REFERENCES]->(n:{label} {{key: $key}})
RETURN 'in' AS direction, type(r) AS link, labels(m)[0] AS label, m.key AS key,
       m.title AS title, m.url AS url, m.state AS state
"""

# Files and Components touched: by the PR itself, or by PRs linked to the issue.
_TOUCHED = """
MATCH (n:{label} {{key: $key}})
OPTIONAL MATCH (n)-[:FIXES|REFERENCES]-(linked:PullRequest)
WITH n, CASE WHEN n:PullRequest THEN [n] ELSE [] END + collect(DISTINCT linked) AS prs
UNWIND prs AS pr
MATCH (pr)-[:MODIFIES]->(f:File)-[:IN_COMPONENT]->(c:Component)
RETURN DISTINCT pr.key AS pr, pr.title AS pr_title, pr.url AS pr_url,
       f.key AS file, f.path AS path, c.key AS component, c.name AS component_name
LIMIT 60
"""

OVERLAPPING_PRS = """
UNWIND $files AS file_key
MATCH (f:File {key: file_key})<-[:MODIFIES]-(other:PullRequest)
WHERE NOT other.key IN $exclude
WITH other, collect(DISTINCT f.key) AS shared
RETURN other.key AS key, other.title AS title, other.url AS url, other.state AS state,
       other.merged_at AS merged_at, shared
ORDER BY other.state = 'OPEN' DESC, size(shared) DESC, coalesce(other.merged_at, 0) DESC
LIMIT $limit
"""


class RelatedWorkArgs(BaseModel):
    key: str = Field(description="Issue or PR key, e.g. 'FalkorDB/FalkorDB#1234'.")
    limit: int = Field(default=8, ge=1, le=30)


def related_work(graph: OrgGraph, args: RelatedWorkArgs) -> ToolResult:
    item = as_dicts(graph.ro_query(FIND_ITEM, {"key": args.key}))[0]
    label = item["label"]
    cypher = [FIND_ITEM.strip()]
    if label is None:
        return ToolResult(
            tool="related_work",
            args=args.model_dump(),
            rows=[],
            evidence=EvidenceBuilder().build(),
            cypher=cypher,
        )

    links_q = _LINKS.format(label=label)
    touched_q = _TOUCHED.format(label=label)
    links = as_dicts(graph.ro_query(links_q, {"key": args.key}))
    touched = as_dicts(graph.ro_query(touched_q, {"key": args.key}))
    own_prs = sorted({t["pr"] for t in touched})
    files = sorted({t["file"] for t in touched})
    overlapping = (
        as_dicts(
            graph.ro_query(
                OVERLAPPING_PRS,
                {"files": files, "exclude": [args.key, *own_prs], "limit": args.limit},
            )
        )
        if files
        else []
    )
    cypher += [links_q.strip(), touched_q.strip(), OVERLAPPING_PRS.strip()]

    evidence = EvidenceBuilder()
    me = evidence.node(label, args.key, title=item["title"], url=item["url"])
    for link in links:
        other = evidence.node(link["label"], link["key"], title=link["title"], url=link["url"])
        if link["direction"] == "out":
            evidence.edge(me, link["link"], other)
        else:
            evidence.edge(other, link["link"], me)
    for t in touched:
        pr_id = evidence.node("PullRequest", t["pr"], title=t["pr_title"], url=t["pr_url"])
        file_id = evidence.node("File", t["file"], title=t["path"])
        comp_id = evidence.node("Component", t["component"], title=t["component_name"])
        evidence.edge(pr_id, "MODIFIES", file_id)
        evidence.edge(file_id, "IN_COMPONENT", comp_id)
    for o in overlapping:
        other_id = evidence.node("PullRequest", o["key"], title=o["title"], url=o["url"])
        for shared in o["shared"][:3]:
            evidence.edge(other_id, "MODIFIES", f"File:{shared}")

    row: dict[str, Any] = {
        "item": {
            "key": args.key,
            "type": label,
            "title": item["title"],
            "state": item["state"],
            "url": item["url"],
        },
        "linked": [
            {k: link[k] for k in ("key", "label", "title", "state", "url", "link", "direction")}
            for link in links
        ],
        "components": sorted({t["component"] for t in touched}),
        "files": [t["path"] for t in {t["file"]: t for t in touched}.values()][:20],
        "overlapping_prs": [
            {k: o[k] for k in ("key", "title", "state", "url")}
            | {
                "merged": iso(o["merged_at"]),
                "shared_files": [s.split(":", 1)[1] for s in o["shared"]],
            }
            for o in overlapping
        ],
    }
    return ToolResult(
        tool="related_work",
        args=args.model_dump(),
        rows=[row],
        evidence=evidence.build(),
        cypher=cypher,
    )
