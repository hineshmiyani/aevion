"""Write normalised records into an org graph. Every write is a MERGE on a stable key,
so loading the same data twice changes nothing (SPEC success criterion 1).

References are stored as key lists on each Issue/PullRequest and turned into FIXES and
REFERENCES edges by `link_references()` after all repos are loaded, so cross-repo links
resolve regardless of ingestion order.
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

UPSERT_LABELS = """
UNWIND $rows AS row
MERGE (l:Label {key: row.key})
SET l.name = row.name, l.color = row.color, l.repo = row.repo
"""

UPSERT_PULL_REQUESTS = """
UNWIND $rows AS row
MATCH (r:Repo {full_name: row.repo})
MERGE (pr:PullRequest {key: row.key})
SET pr.number = row.number, pr.title = row.title, pr.body_excerpt = row.body_excerpt,
    pr.state = row.state, pr.url = row.url, pr.created_at = row.created_at,
    pr.merged_at = row.merged_at, pr.closed_at = row.closed_at, pr.updated_at = row.updated_at,
    pr.additions = row.additions, pr.deletions = row.deletions,
    pr.ref_keys = row.ref_keys, pr.fix_keys = row.fix_keys
MERGE (pr)-[:IN_REPO]->(r)
"""

UPSERT_ISSUES = """
UNWIND $rows AS row
MATCH (r:Repo {full_name: row.repo})
MERGE (i:Issue {key: row.key})
SET i.number = row.number, i.title = row.title, i.body_excerpt = row.body_excerpt,
    i.state = row.state, i.url = row.url, i.created_at = row.created_at,
    i.closed_at = row.closed_at, i.updated_at = row.updated_at, i.ref_keys = row.ref_keys
MERGE (i)-[:IN_REPO]->(r)
"""

UPSERT_PR_AUTHORED = """
UNWIND $rows AS row
MATCH (p:Person {login: row.login}), (pr:PullRequest {key: row.key})
MERGE (p)-[a:AUTHORED]->(pr)
SET a.at = row.at
"""

UPSERT_ISSUE_AUTHORED = """
UNWIND $rows AS row
MATCH (p:Person {login: row.login}), (i:Issue {key: row.key})
MERGE (p)-[a:AUTHORED]->(i)
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

UPSERT_PR_LABELS = """
UNWIND $rows AS row
MATCH (pr:PullRequest {key: row.key}), (l:Label {key: row.label})
MERGE (pr)-[:HAS_LABEL]->(l)
"""

UPSERT_ISSUE_LABELS = """
UNWIND $rows AS row
MATCH (i:Issue {key: row.key}), (l:Label {key: row.label})
MERGE (i)-[:HAS_LABEL]->(l)
"""

UPSERT_ASSIGNED = """
UNWIND $rows AS row
MATCH (i:Issue {key: row.key}), (p:Person {login: row.login})
MERGE (i)-[:ASSIGNED_TO]->(p)
"""

_UPSERT_COMMENTS = """
UNWIND $rows AS row
MATCH (t:{label} {{key: row.thread_key}}), (p:Person {{login: row.author}})
MERGE (c:Comment {{id: row.id}})
SET c.kind = row.kind, c.excerpt = row.excerpt, c.url = row.url, c.created_at = row.created_at
MERGE (c)-[:ON]->(t)
MERGE (p)-[a:AUTHORED]->(c)
SET a.at = row.created_at
"""
UPSERT_PR_COMMENTS = _UPSERT_COMMENTS.format(label="PullRequest")
UPSERT_ISSUE_COMMENTS = _UPSERT_COMMENTS.format(label="Issue")

UPSERT_RELEASES = """
UNWIND $rows AS row
MATCH (r:Repo {full_name: row.repo})
MERGE (rel:Release {key: row.key})
SET rel.tag = row.tag, rel.name = row.name, rel.url = row.url,
    rel.published_at = row.published_at, rel.pr_keys = row.pr_keys
MERGE (rel)-[:IN_REPO]->(r)
"""

_UPSERT_OWNS = """
UNWIND $rows AS row
MATCH (r:Repo {{full_name: row.repo}})
MERGE (c:Component {{key: row.component_key}})
SET c.name = coalesce(c.name, row.component_path), c.repo = row.repo,
    c.path_prefix = coalesce(c.path_prefix, row.component_path),
    c.source = coalesce(c.source, 'codeowners')
MERGE (c)-[:IN_REPO]->(r)
MERGE (o:{label} {{{key}: row.owner}})
{on_owner}
MERGE (o)-[own:OWNS {{valid_from: row.valid_from}}]->(c)
SET own.valid_to = row.valid_to, own.source = 'CODEOWNERS'
"""
UPSERT_PERSON_OWNS = _UPSERT_OWNS.format(
    label="Person", key="login", on_owner="SET o.is_bot = coalesce(o.is_bot, false)"
)
UPSERT_TEAM_OWNS = _UPSERT_OWNS.format(label="Team", key="key", on_owner="SET o.name = row.owner")

_LINK = """
MATCH (s:{source}) WHERE size(s.{keys}) > 0
UNWIND s.{keys} AS k
MATCH (t:{target} {{key: k}})
MERGE (s)-[:{edge}]->(t)
"""
LINK_QUERIES = (
    _LINK.format(source="PullRequest", keys="fix_keys", target="Issue", edge="FIXES"),
    _LINK.format(source="Release", keys="pr_keys", target="PullRequest", edge="INCLUDES"),
    *(
        _LINK.format(source=source, keys="ref_keys", target=target, edge="REFERENCES")
        for source in ("PullRequest", "Issue")
        for target in ("PullRequest", "Issue")
    ),
)


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
    """Nodes first, then edges that MATCH both ends."""
    _run(graph, UPSERT_PEOPLE, [asdict(p) for p in batch.people.values()])
    _run(graph, UPSERT_LABELS, [asdict(label) for label in batch.labels.values()])

    prs = batch.pull_requests
    _run(
        graph,
        UPSERT_PULL_REQUESTS,
        [{k: v for k, v in asdict(pr).items() if k not in ("reviews", "files")} for pr in prs],
    )
    _run(
        graph,
        UPSERT_PR_AUTHORED,
        [{"login": pr.author, "key": pr.key, "at": pr.created_at} for pr in prs if pr.author],
    )
    _run(
        graph,
        UPSERT_REVIEWED,
        [
            {"login": r.login, "key": pr.key, "state": r.state, "at": r.at}
            for pr in prs
            for r in pr.reviews
            if r.login != pr.author  # self-reviews add no expertise signal
        ],
    )
    _run(
        graph,
        UPSERT_FILES,
        [{**asdict(f), "repo": pr.repo, "pr_key": pr.key} for pr in prs for f in pr.files],
    )
    _run(graph, UPSERT_PR_LABELS, [{"key": pr.key, "label": lb} for pr in prs for lb in pr.labels])

    issues = batch.issues
    _run(graph, UPSERT_ISSUES, [asdict(i) for i in issues])
    _run(
        graph,
        UPSERT_ISSUE_AUTHORED,
        [{"login": i.author, "key": i.key, "at": i.created_at} for i in issues if i.author],
    )
    _run(
        graph, UPSERT_ISSUE_LABELS, [{"key": i.key, "label": lb} for i in issues for lb in i.labels]
    )
    _run(graph, UPSERT_ASSIGNED, [{"key": i.key, "login": a} for i in issues for a in i.assignees])

    _run(graph, UPSERT_RELEASES, [asdict(r) for r in batch.releases])
    owns = [asdict(o) for o in batch.ownerships]
    _run(graph, UPSERT_PERSON_OWNS, [o for o in owns if o["kind"] == "person"])
    _run(graph, UPSERT_TEAM_OWNS, [o for o in owns if o["kind"] == "team"])

    pr_keys = {pr.key for pr in prs}
    comments = [asdict(c) for c in batch.comments]
    _run(graph, UPSERT_PR_COMMENTS, [c for c in comments if c["thread_key"] in pr_keys])
    _run(graph, UPSERT_ISSUE_COMMENTS, [c for c in comments if c["thread_key"] not in pr_keys])


UNLINK_FILE_COMPONENTS = """
MATCH (f:File {repo: $repo})-[r:IN_COMPONENT]->(:Component)
DELETE r
"""

PRUNE_ORPHAN_COMPONENTS = """
MATCH (c:Component {repo: $repo})
WHERE NOT ()-[:IN_COMPONENT]->(c) AND NOT ()-[:OWNS]->(c)
DETACH DELETE c
"""


def unlink_file_components(graph: OrgGraph, repo: str) -> None:
    """Before re-ingesting with a new component depth: drop File→Component links only."""
    graph.query(UNLINK_FILE_COMPONENTS, {"repo": repo})


def prune_orphan_components(graph: OrgGraph, repo: str) -> int:
    """After re-ingesting: delete Components nothing links to any more."""
    before = graph.ro_query("MATCH (c:Component {repo: $repo}) RETURN count(c)", {"repo": repo})
    graph.query(PRUNE_ORPHAN_COMPONENTS, {"repo": repo})
    after = graph.ro_query("MATCH (c:Component {repo: $repo}) RETURN count(c)", {"repo": repo})
    return int(before.rows[0][0]) - int(after.rows[0][0])


def link_references(graph: OrgGraph) -> None:
    """Create FIXES / REFERENCES edges from the stored key lists. Idempotent."""
    for query in LINK_QUERIES:
        graph.query(query)


def graph_counts(graph: OrgGraph) -> dict[str, int]:
    nodes = graph.ro_query("MATCH (n) RETURN count(n)").rows[0][0]
    edges = graph.ro_query("MATCH ()-[r]->() RETURN count(r)").rows[0][0]
    return {"nodes": int(nodes), "edges": int(edges)}


def _run(graph: OrgGraph, query: str, rows: list[dict[str, Any]]) -> None:
    if rows:
        graph.query(query, {"rows": rows})
