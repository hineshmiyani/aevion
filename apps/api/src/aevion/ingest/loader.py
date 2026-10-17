"""Write normalised records into an org graph. Every write is a MERGE on a stable key,
so loading the same data twice changes nothing (SPEC success criterion 1).
"""

from dataclasses import asdict
from typing import Any

from aevion.graph.client import OrgGraph
from aevion.ingest.normalize import Batch

UPSERT_REPO = """
MERGE (r:Repo {full_name: $full_name})
SET r.name = $name, r.url = $url, r.stars = $stars, r.default_branch = $default_branch
"""

UPSERT_PEOPLE = """
UNWIND $rows AS row
MERGE (p:Person {login: row.login})
SET p.is_bot = row.is_bot, p.avatar_url = row.avatar_url
"""

UPSERT_PULL_REQUESTS = """
UNWIND $rows AS row
MATCH (r:Repo {full_name: row.repo})
MERGE (pr:PullRequest {key: row.key})
SET pr.number = row.number, pr.title = row.title, pr.body_excerpt = row.body_excerpt,
    pr.state = row.state, pr.url = row.url, pr.created_at = row.created_at,
    pr.merged_at = row.merged_at, pr.closed_at = row.closed_at, pr.updated_at = row.updated_at,
    pr.additions = row.additions, pr.deletions = row.deletions
MERGE (pr)-[:IN_REPO]->(r)
"""

UPSERT_AUTHORED = """
UNWIND $rows AS row
MATCH (p:Person {login: row.login}), (pr:PullRequest {key: row.key})
MERGE (p)-[a:AUTHORED]->(pr)
SET a.at = row.at
"""

UPSERT_REVIEWED = """
UNWIND $rows AS row
MATCH (p:Person {login: row.login}), (pr:PullRequest {key: row.key})
MERGE (p)-[rv:REVIEWED]->(pr)
SET rv.state = row.state, rv.at = row.at
"""

UPSERT_FILES = """
UNWIND $rows AS row
MATCH (r:Repo {full_name: row.repo}), (pr:PullRequest {key: row.pr_key})
MERGE (c:Component {key: row.component_key})
SET c.name = row.component_path, c.repo = row.repo, c.path_prefix = row.component_path,
    c.source = 'path'
MERGE (c)-[:IN_REPO]->(r)
MERGE (f:File {key: row.file_key})
SET f.path = row.path, f.repo = row.repo, f.is_doc = row.is_doc
MERGE (f)-[:IN_COMPONENT]->(c)
MERGE (pr)-[m:MODIFIES]->(f)
SET m.additions = row.additions, m.deletions = row.deletions
"""


def upsert_repo(graph: OrgGraph, repository: dict[str, Any]) -> str:
    full_name: str = repository["nameWithOwner"]
    graph.query(
        UPSERT_REPO,
        {
            "full_name": full_name,
            "name": full_name.split("/", 1)[1],
            "url": repository["url"],
            "stars": repository.get("stargazerCount", 0),
            "default_branch": (repository.get("defaultBranchRef") or {}).get("name"),
        },
    )
    return full_name


def load_batch(graph: OrgGraph, batch: Batch) -> None:
    """People first, then PRs, then edges that MATCH both ends."""
    if batch.people:
        graph.query(UPSERT_PEOPLE, {"rows": [asdict(p) for p in batch.people.values()]})
    if not batch.pull_requests:
        return

    prs = batch.pull_requests
    graph.query(
        UPSERT_PULL_REQUESTS,
        {
            "rows": [
                {k: v for k, v in asdict(pr).items() if k not in ("reviews", "files")} for pr in prs
            ]
        },
    )
    authored = [{"login": pr.author, "key": pr.key, "at": pr.created_at} for pr in prs if pr.author]
    if authored:
        graph.query(UPSERT_AUTHORED, {"rows": authored})
    reviewed = [
        {"login": r.login, "key": pr.key, "state": r.state, "at": r.at}
        for pr in prs
        for r in pr.reviews
        if r.login != pr.author  # self-reviews add no expertise signal
    ]
    if reviewed:
        graph.query(UPSERT_REVIEWED, {"rows": reviewed})
    files = [{**asdict(f), "repo": pr.repo, "pr_key": pr.key} for pr in prs for f in pr.files]
    if files:
        graph.query(UPSERT_FILES, {"rows": files})


def graph_counts(graph: OrgGraph) -> dict[str, int]:
    nodes = graph.ro_query("MATCH (n) RETURN count(n)").rows[0][0]
    edges = graph.ro_query("MATCH ()-[r]->() RETURN count(r)").rows[0][0]
    return {"nodes": int(nodes), "edges": int(edges)}
