"""catch_up: what changed in a Component or repo since a date, and who drove it? (US-5)"""

from typing import Any

from pydantic import BaseModel, Field, model_validator

from aevion.graph.client import OrgGraph
from aevion.tools.evidence import EvidenceBuilder, ToolResult
from aevion.tools.scope import as_dicts, iso, resolve_components, since_ms

# Merged PRs that touched the given Components...
MERGED_PRS_IN_COMPONENTS = """
MATCH (c:Component)<-[:IN_COMPONENT]-(:File)<-[:MODIFIES]-(pr:PullRequest)-[:IN_REPO]->(r:Repo)
WHERE c.key IN $components AND pr.merged_at >= $since
WITH DISTINCT pr, r
OPTIONAL MATCH (a:Person)-[:AUTHORED]->(pr)
RETURN pr.key AS key, pr.title AS title, pr.url AS url, pr.merged_at AS merged_at,
       a.login AS author, coalesce(a.is_bot, false) AS bot, r.full_name AS repo
ORDER BY merged_at DESC
"""

# ...or every merged PR in a repo when no Component is given.
MERGED_PRS_IN_REPO = """
MATCH (pr:PullRequest)-[:IN_REPO]->(r:Repo {full_name: $repo})
WHERE pr.merged_at >= $since
OPTIONAL MATCH (a:Person)-[:AUTHORED]->(pr)
RETURN pr.key AS key, pr.title AS title, pr.url AS url, pr.merged_at AS merged_at,
       a.login AS author, coalesce(a.is_bot, false) AS bot, r.full_name AS repo
ORDER BY merged_at DESC
"""

CLOSED_ISSUES = """
UNWIND $prs AS pr_key
MATCH (pr:PullRequest {key: pr_key})-[:FIXES]->(i:Issue)
WHERE i.closed_at >= $since
RETURN DISTINCT i.key AS key, i.title AS title, i.url AS url, i.closed_at AS closed_at,
       pr.key AS fixed_by
"""

RELEASES = """
MATCH (rel:Release)-[:IN_REPO]->(r:Repo)
WHERE rel.published_at >= $since AND ($repo IS NULL OR r.full_name = $repo)
  AND (size($repos) = 0 OR r.full_name IN $repos)
RETURN rel.key AS key, rel.tag AS tag, rel.url AS url, rel.published_at AS published_at,
       r.full_name AS repo
ORDER BY published_at DESC
LIMIT 10
"""


class CatchUpArgs(BaseModel):
    component: str | None = Field(default=None, description="Component key or path fragment.")
    repo: str | None = Field(default=None, description="Repo, e.g. 'FalkorDB/GraphRAG-SDK'.")
    since: str = Field(description="ISO date to catch up from, e.g. '2026-10-01'.")
    limit: int = Field(default=15, ge=1, le=50)

    @model_validator(mode="after")
    def _needs_scope(self) -> "CatchUpArgs":
        if not self.component and not self.repo:
            raise ValueError("give a component or a repo")
        return self


def catch_up(graph: OrgGraph, args: CatchUpArgs) -> ToolResult:
    components = resolve_components(graph, args.component, args.repo) if args.component else []
    keys = [row[0] for row in components]
    since = since_ms(iso_date=args.since)
    if args.component and not keys:
        return ToolResult(
            tool="catch_up",
            args=args.model_dump(),
            rows=[],
            evidence=EvidenceBuilder().build(),
            cypher=[],
        )

    params: dict[str, Any] = {"since": since, "repo": args.repo, "components": keys}
    merged_q = MERGED_PRS_IN_COMPONENTS if keys else MERGED_PRS_IN_REPO
    prs = as_dicts(graph.ro_query(merged_q, params))
    human = [pr for pr in prs if not pr["bot"]]
    issues = as_dicts(
        graph.ro_query(CLOSED_ISSUES, {"prs": [p["key"] for p in prs], "since": since})
    )
    repos = sorted({row[2] for row in components}) if keys else []
    releases = as_dicts(
        graph.ro_query(RELEASES, {"since": since, "repo": args.repo, "repos": repos})
    )

    drivers: dict[str, int] = {}
    for pr in human:
        if pr["author"]:
            drivers[pr["author"]] = drivers.get(pr["author"], 0) + 1

    evidence = EvidenceBuilder()
    for key, name, _repo in components:
        evidence.node("Component", key, title=name)
    shown = human[: args.limit]
    for pr in shown:
        pr_id = evidence.node("PullRequest", pr["key"], title=pr["title"], url=pr["url"])
        if pr["author"]:
            evidence.edge(evidence.node("Person", pr["author"]), "AUTHORED", pr_id)
    shown_keys = {pr["key"] for pr in shown}
    for issue in issues:
        if issue["fixed_by"] in shown_keys:
            evidence.edge(
                f"PullRequest:{issue['fixed_by']}",
                "FIXES",
                evidence.node("Issue", issue["key"], title=issue["title"], url=issue["url"]),
            )

    row = {
        "since": args.since,
        "scope": {"components": keys, "repo": args.repo},
        "merged_prs": len(prs),
        "merged_prs_by_bots": len(prs) - len(human),
        "highlights": [
            {k: pr[k] for k in ("key", "title", "url", "author")} | {"merged": iso(pr["merged_at"])}
            for pr in shown
        ],
        "closed_issues": [
            {k: i[k] for k in ("key", "title", "url", "fixed_by")} | {"closed": iso(i["closed_at"])}
            for i in issues
        ],
        "releases": [
            {k: r[k] for k in ("tag", "url", "repo")} | {"published": iso(r["published_at"])}
            for r in releases
        ],
        "drivers": [
            {"login": login, "merged_prs": n}
            for login, n in sorted(drivers.items(), key=lambda kv: -kv[1])[:5]
        ],
    }
    return ToolResult(
        tool="catch_up",
        args=args.model_dump(),
        rows=[row],
        evidence=evidence.build(),
        cypher=[merged_q.strip(), CLOSED_ISSUES.strip(), RELEASES.strip()],
    )
