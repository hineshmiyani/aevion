"""area_history: what's the history of a Component? (US-3)

Recent merged PRs, open issues connected to that code, and the people most active there.
"""

from typing import Any

from pydantic import BaseModel, Field

from aevion.graph.client import OrgGraph
from aevion.tools.evidence import EvidenceBuilder, ToolResult
from aevion.tools.scope import as_dicts, iso, resolve_components, since_ms

RECENT_PRS = """
MATCH (c:Component)<-[:IN_COMPONENT]-(f:File)<-[:MODIFIES]-(pr:PullRequest)
WHERE c.key IN $components AND pr.merged_at >= $since
WITH pr, collect(f.key)[0] AS file, collect(c.key)[0] AS component
OPTIONAL MATCH (a:Person)-[:AUTHORED]->(pr)
RETURN pr.key AS key, pr.title AS title, pr.url AS url, pr.merged_at AS merged_at,
       a.login AS author, file, component
ORDER BY merged_at DESC
LIMIT $limit
"""

# Open issues tied to the Component's code: fixed or referenced by PRs that touched it,
# in either direction (an issue can reference a PR too).
OPEN_ISSUES = """
MATCH (c:Component)<-[:IN_COMPONENT]-(f:File)<-[:MODIFIES]-(pr:PullRequest)
WHERE c.key IN $components
MATCH (pr)-[r:FIXES|REFERENCES]-(i:Issue)
WHERE i.state = 'OPEN'
WITH i, pr, r, f, c
RETURN DISTINCT i.key AS key, i.title AS title, i.url AS url, i.created_at AS created_at,
       pr.key AS via_pr, pr.title AS via_title, pr.url AS via_url, type(r) AS link,
       startNode(r) = pr AS from_pr, f.key AS file, c.key AS component
LIMIT $limit
"""

ACTIVE_PEOPLE = """
MATCH (c:Component)<-[:IN_COMPONENT]-(:File)<-[:MODIFIES]-(pr:PullRequest)
WHERE c.key IN $components AND pr.merged_at >= $since
MATCH (p:Person)-[r:AUTHORED|REVIEWED]->(pr)
WHERE NOT p.is_bot
WITH p, count(DISTINCT CASE type(r) WHEN 'AUTHORED' THEN pr END) AS authored,
     count(DISTINCT CASE type(r) WHEN 'REVIEWED' THEN pr END) AS reviewed
RETURN p.login AS login, authored, reviewed
ORDER BY authored + reviewed DESC
LIMIT 5
"""


class AreaHistoryArgs(BaseModel):
    component: str = Field(description="Component key or path fragment, e.g. 'execution_plan'.")
    repo: str | None = Field(default=None, description="Restrict to one repo.")
    days: int = Field(default=90, ge=1, le=365, description="How far back to look.")
    limit: int = Field(default=10, ge=1, le=30)


def area_history(graph: OrgGraph, args: AreaHistoryArgs) -> ToolResult:
    components = resolve_components(graph, args.component, args.repo)
    keys = [row[0] for row in components]
    params: dict[str, Any] = {"components": keys, "since": since_ms(args.days), "limit": args.limit}
    prs = as_dicts(graph.ro_query(RECENT_PRS, params)) if keys else []
    linked = as_dicts(graph.ro_query(OPEN_ISSUES, params)) if keys else []
    # An issue linked to several PRs comes back once per PR; keep the first link as evidence.
    issues = list({issue["key"]: issue for issue in reversed(linked)}.values())[::-1]
    people = as_dicts(graph.ro_query(ACTIVE_PEOPLE, params)) if keys else []

    evidence = EvidenceBuilder()
    for key, name, _repo in components:
        evidence.node("Component", key, title=name)
    for pr in prs:
        pr_id = evidence.node("PullRequest", pr["key"], title=pr["title"], url=pr["url"])
        file_id = evidence.node("File", pr["file"], title=pr["file"].split(":", 1)[1])
        evidence.edge(pr_id, "MODIFIES", file_id)
        evidence.edge(file_id, "IN_COMPONENT", f"Component:{pr['component']}")
        if pr["author"]:
            evidence.edge(evidence.node("Person", pr["author"]), "AUTHORED", pr_id)
    for issue in issues:
        issue_id = evidence.node("Issue", issue["key"], title=issue["title"], url=issue["url"])
        pr_id = evidence.node(
            "PullRequest", issue["via_pr"], title=issue["via_title"], url=issue["via_url"]
        )
        file_id = evidence.node("File", issue["file"], title=issue["file"].split(":", 1)[1])
        evidence.edge(pr_id, "MODIFIES", file_id)
        evidence.edge(file_id, "IN_COMPONENT", f"Component:{issue['component']}")
        if issue["from_pr"]:
            evidence.edge(pr_id, issue["link"], issue_id)
        else:
            evidence.edge(issue_id, issue["link"], pr_id)

    rows = (
        [
            {
                "components": [row[0] for row in components],
                "recent_prs": [
                    {k: pr[k] for k in ("key", "title", "url", "author")}
                    | {"merged": iso(pr["merged_at"])}
                    for pr in prs
                ],
                "open_issues": [
                    {k: i[k] for k in ("key", "title", "url", "via_pr", "link")}
                    | {"opened": iso(i["created_at"])}
                    for i in issues
                ],
                "active_people": people,
            }
        ]
        if keys
        else []
    )
    return ToolResult(
        tool="area_history",
        args=args.model_dump(),
        rows=rows,
        evidence=evidence.build(),
        cypher=[RECENT_PRS.strip(), OPEN_ISSUES.strip(), ACTIVE_PEOPLE.strip()],
    )
