"""experts_for: who knows a Component? (US-1, GLOSSARY: Expert)

Expertise is computed live from the graph at question time (ADR-0011 §3): weighted, recent
merged-PR activity in the Component. Weights and decay are design constants, documented in
docs/architecture/cypher-queries.md so the team can explain them (Rule 12).
"""

from typing import Any

from pydantic import BaseModel, Field

from aevion.graph.client import OrgGraph
from aevion.tools.evidence import EvidenceBuilder, ToolResult

AUTHORED_WEIGHT = 3.0
REVIEWED_WEIGHT = 2.0
COMMENT_WEIGHT = 0.5
DECAY_DAYS = 260.0  # exp(-age/260) halves a contribution's weight after ~180 days
EVIDENCE_PER_PERSON = 3


class ExpertsForArgs(BaseModel):
    component: str = Field(
        description="Component key (e.g. 'FalkorDB/FalkorDB:src/execution_plan') or a path "
        "fragment to search for (e.g. 'execution_plan')."
    )
    repo: str | None = Field(
        default=None, description="Restrict to one repo, e.g. 'FalkorDB/FalkorDB'."
    )
    limit: int = Field(default=5, ge=1, le=20)


# Components matching an exact key, or a path fragment (optionally within one repo).
MATCH_COMPONENTS = """
MATCH (c:Component)
WHERE (c.key = $component OR toLower(c.path_prefix) CONTAINS toLower($component))
  AND ($repo IS NULL OR c.repo = $repo)
RETURN c.key, c.name, c.repo
ORDER BY c.key = $component DESC, size(c.path_prefix)
LIMIT 5
"""

# Merged PRs in those Components, scored per person by role and recency.
SCORE_PR_ACTIVITY = """
MATCH (c:Component)<-[:IN_COMPONENT]-(f:File)<-[:MODIFIES]-(pr:PullRequest)
WHERE c.key IN $components AND pr.merged_at IS NOT NULL
MATCH (p:Person)-[r:AUTHORED|REVIEWED]->(pr)
WHERE NOT p.is_bot
WITH p, pr, type(r) AS role, collect(f.key)[0] AS file, collect(c.key)[0] AS component,
     exp(-((timestamp() - pr.merged_at) / 86400000.0) / $decay) AS recency
RETURN p.login AS login, pr.key AS pr, pr.title AS title, pr.url AS url, pr.merged_at AS at,
       role, file, component,
       CASE role WHEN 'AUTHORED' THEN $authored ELSE $reviewed END * recency AS points
"""

# Human comments on those same PRs.
SCORE_COMMENTS = """
MATCH (c:Component)<-[:IN_COMPONENT]-(:File)<-[:MODIFIES]-(pr:PullRequest)
WHERE c.key IN $components AND pr.merged_at IS NOT NULL
MATCH (p:Person)-[:AUTHORED]->(cm:Comment)-[:ON]->(pr)
WHERE NOT p.is_bot
WITH DISTINCT p, cm, pr
RETURN p.login AS login, cm.id AS comment, cm.url AS url, pr.key AS pr,
       $comment * exp(-((timestamp() - cm.created_at) / 86400000.0) / $decay) AS points
"""


def experts_for(graph: OrgGraph, args: ExpertsForArgs) -> ToolResult:
    components = graph.ro_query(
        MATCH_COMPONENTS, {"component": args.component, "repo": args.repo}
    ).rows
    component_keys = [row[0] for row in components]
    params = {
        "components": component_keys,
        "decay": DECAY_DAYS,
        "authored": AUTHORED_WEIGHT,
        "reviewed": REVIEWED_WEIGHT,
        "comment": COMMENT_WEIGHT,
    }
    pr_rows = _as_dicts(graph.ro_query(SCORE_PR_ACTIVITY, params)) if component_keys else []
    comment_rows = _as_dicts(graph.ro_query(SCORE_COMMENTS, params)) if component_keys else []

    people: dict[str, dict[str, Any]] = {}
    for row in pr_rows:
        person = _person(people, row["login"])
        person["score"] += row["points"]
        person["authored" if row["role"] == "AUTHORED" else "reviewed"] += 1
        person["_prs"].append(row)
    for row in comment_rows:
        person = _person(people, row["login"])
        person["score"] += row["points"]
        person["comments"] += 1

    ranked = sorted(people.values(), key=lambda p: p["score"], reverse=True)[: args.limit]

    evidence = EvidenceBuilder()
    for key, name, _repo in components:
        evidence.node("Component", key, title=name)
    rows: list[dict[str, Any]] = []
    for person in ranked:
        strongest = sorted(person.pop("_prs"), key=lambda r: r["points"], reverse=True)
        top = strongest[:EVIDENCE_PER_PERSON]
        person_id = evidence.node(
            "Person", person["login"], url=f"https://github.com/{person['login']}"
        )
        for pr in top:
            pr_id = evidence.node("PullRequest", pr["pr"], title=pr["title"], url=pr["url"])
            file_id = evidence.node("File", pr["file"], title=pr["file"].split(":", 1)[1])
            evidence.edge(person_id, pr["role"], pr_id)
            evidence.edge(pr_id, "MODIFIES", file_id)
            evidence.edge(file_id, "IN_COMPONENT", f"Component:{pr['component']}")
        rows.append(
            {
                "login": person["login"],
                "score": round(person["score"], 2),
                "authored_prs": person["authored"],
                "reviewed_prs": person["reviewed"],
                "comments": person["comments"],
                "evidence": [
                    {"pr": r["pr"], "title": r["title"], "url": r["url"], "role": r["role"]}
                    for r in top
                ],
            }
        )

    return ToolResult(
        tool="experts_for",
        args=args.model_dump(),
        rows=rows,
        evidence=evidence.build(),
        cypher=[MATCH_COMPONENTS.strip(), SCORE_PR_ACTIVITY.strip(), SCORE_COMMENTS.strip()],
    )


def _person(people: dict[str, dict[str, Any]], login: str) -> dict[str, Any]:
    return people.setdefault(
        login,
        {"login": login, "score": 0.0, "authored": 0, "reviewed": 0, "comments": 0, "_prs": []},
    )


def _as_dicts(result: Any) -> list[dict[str, Any]]:
    return [dict(zip(result.columns, row, strict=True)) for row in result.rows]
