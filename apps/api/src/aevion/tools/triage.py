"""triage_candidates: what is this issue about, and who should look at it? (US-6)

A new issue has no edges of its own yet, so the graph answers by analogy:

1. Similar issues: full-text search over Issue(title, body_excerpt), re-ranked by how much of
   this issue's title each candidate's title covers. High coverage means a likely duplicate.
2. Components, by vote: the Components that similar issues' fixing PRs touched
   (Issue <-FIXES- PR -MODIFIES-> File -IN_COMPONENT-> Component), each PR's vote split across
   the Components it touched; the Components of any file the issue names by path; Components
   whose path words match the issue title's keywords ("UDF" -> src/udf); and this issue's own fixing
   PRs if it already has some. Tests, CI, build and root folders never vote.
3. Experts: experts_for on the winning Component, minus the issue's author.

Every step is a graph traversal, and every edge in the evidence path exists in the graph.
"""

import re
from typing import Any

from pydantic import BaseModel, Field

from aevion.graph.client import OrgGraph
from aevion.tools.evidence import EvidenceBuilder, EvidencePath, ToolResult
from aevion.tools.experts import ExpertsForArgs, experts_for
from aevion.tools.scope import as_dicts
from aevion.tools.text import coverage, keyword_stems, keywords

SIMILAR_POOL = 40
DUPLICATE_COVERAGE = 0.6  # share of this issue's title keywords a likely duplicate's title has
OWN_FIX_WEIGHT = 2.0  # a PR that already fixes this issue is the strongest Component signal
MENTION_WEIGHT = 1.5  # a file the issue names by path
NAME_WEIGHT = 0.5  # per issue keyword found in a Component's path words
STRONG_VOTES = 1.0  # e.g. this issue's own fix, or several similar fixes agreeing
MODERATE_VOTES = 0.4
VOTERS = 12  # similar issues whose fixes vote (more than are shown)
MAX_QUERY_WORDS = 12
# Folders that say nothing about which part of the product an issue is about, at any depth.
_INFRA = frozenset(
    {
        "(root)",
        "assets",
        "test",
        "tests",
        "build",
        "ci",
        "script",
        "scripts",
        "doc",
        "docs",
        "deps",
        "example",
        "examples",
        "demo",
        "demos",
        "benchmark",
        "benchmarks",
    }
)
COMMON_WORD_SHARE = 0.1  # a path word in more of a repo's Components than this can't vote

FIND_ISSUE = """
MATCH (i:Issue {key: $key})-[:IN_REPO]->(r:Repo)
OPTIONAL MATCH (a:Person)-[:AUTHORED]->(i)
RETURN i.title AS title, i.body_excerpt AS body, i.state AS state, i.url AS url,
       r.full_name AS repo, a.login AS author
"""

# Candidates only; Python re-ranks them by title coverage (see tools/text.py).
SIMILAR = """
CALL db.idx.fulltext.queryNodes('Issue', $query) YIELD node, score
WITH node, score WHERE node.key <> $key
MATCH (node)-[:IN_REPO]->(r:Repo)
OPTIONAL MATCH (pr:PullRequest)-[:FIXES]->(node)
RETURN node.key AS key, node.title AS title, node.body_excerpt AS body, node.state AS state,
       node.url AS url, r.full_name AS repo, score, collect(pr.key) AS fixed_by
ORDER BY score DESC
LIMIT $pool
"""

# The code that fixed each issue: which Components did those PRs change? Docs don't vote.
# The WITH matters: as one pattern, FalkorDB planned it from a scan of every File (because of
# the is_doc filter), 800 ms and over the server's 1 s timeout on Railway. Split at the PR, it
# starts from the Issue.key index: 5 ms, same rows.
FIX_COMPONENTS = """
UNWIND $issues AS issue_key
MATCH (i:Issue {key: issue_key})<-[:FIXES]-(pr:PullRequest)
WITH issue_key, pr
MATCH (pr)-[:MODIFIES]->(f:File)-[:IN_COMPONENT]->(c:Component)
WHERE NOT f.is_doc
RETURN issue_key AS issue, pr.key AS pr, pr.title AS pr_title, pr.url AS pr_url,
       f.key AS file, f.path AS path, c.key AS component, c.name AS name
LIMIT 600
"""

# Files the issue names: an exact repo path, or a bare file name matching a path's tail.
# The parentheses matter: FalkorDB reads `ENDS WITH '/' + x` as `(ENDS WITH '/') + x`.
MENTIONED_FILES = """
UNWIND $paths AS mentioned
MATCH (f:File)-[:IN_COMPONENT]->(c:Component)
WHERE f.repo = $repo AND (f.path = mentioned OR f.path ENDS WITH ('/' + mentioned))
RETURN mentioned, f.key AS file, f.path AS path, c.key AS component, c.name AS name
LIMIT 20
"""

REPO_COMPONENTS = """
MATCH (c:Component)
WHERE c.repo = $repo
RETURN c.key AS key, c.name AS name, c.path_prefix AS path
"""

_PATH = re.compile(
    r"(?<![\w/.-])((?:[\w.-]+/)*[\w-]+\.(?:c|h|cc|cpp|hpp|py|ts|tsx|js|jsx|rs|go|java|rb))\b"
)


HINT_WEIGHT = 1.0  # per hint word found; similar issues add their title coverage
MIN_REPO_SCORE = 0.5  # below this, fall back to the default repo


def infer_repo(
    graph: OrgGraph,
    title: str,
    body: str,
    hints: dict[str, tuple[str, ...]],
    default: str,
) -> tuple[str, list[str]]:
    """Which repo is a newly filed issue about? Hint words from the org config, plus the repos
    of the most similar issues across the org. Returns the repo and the reasons, for the UI."""
    text = f"{title}\n{body}".lower()
    scores: dict[str, float] = {}
    reasons: dict[str, list[str]] = {}
    for repo, words in hints.items():
        found = [w for w in words if re.search(rf"(?<![\w-]){re.escape(w)}(?![\w-])", text)]
        if found:
            scores[repo] = scores.get(repo, 0.0) + HINT_WEIGHT * len(found)
            reasons.setdefault(repo, []).append("mentions " + ", ".join(found))
    query = "|".join(keywords(title)[:MAX_QUERY_WORDS])
    if query:
        wanted = keyword_stems(title)
        pool = as_dicts(graph.ro_query(SIMILAR, {"query": query, "key": "", "pool": SIMILAR_POOL}))
        for row in pool:
            row["match"] = coverage(wanted, row["title"])
        for row in sorted(pool, key=lambda r: -r["match"])[:VOTERS]:
            if row["match"] > 0:
                scores[row["repo"]] = scores.get(row["repo"], 0.0) + row["match"]
                reasons.setdefault(row["repo"], []).append(f"like {row['key']}")
    if scores:
        repo, score = max(scores.items(), key=lambda kv: kv[1])
        if score >= MIN_REPO_SCORE:
            return repo, reasons[repo][:4]
    return default, ["no clear signal, so the default repo"]


class TriageCandidatesArgs(BaseModel):
    issue: str = Field(description="Issue key, e.g. 'FalkorDB/FalkorDB#3371'.")
    limit: int = Field(default=5, ge=1, le=10, description="How many similar issues to return.")


def mentioned_paths(text: str) -> list[str]:
    """File paths or file names written in an issue, e.g. 'src/graph/graph.c' or 'op_merge.c'."""
    return list(dict.fromkeys(m.group(1).lstrip("./") for m in _PATH.finditer(text or "")))[:10]


def triage_candidates(graph: OrgGraph, args: TriageCandidatesArgs) -> ToolResult:
    found = as_dicts(graph.ro_query(FIND_ISSUE, {"key": args.issue}))
    if not found:
        return ToolResult(
            tool="triage_candidates",
            args=args.model_dump(),
            rows=[],
            evidence=EvidencePath(),
            cypher=[FIND_ISSUE.strip()],
        )
    issue = {**found[0], "key": args.issue}
    return triage_issue(graph, issue, args.limit, cypher=[FIND_ISSUE.strip()])


def triage_issue(
    graph: OrgGraph, issue: dict[str, Any], limit: int = 5, *, cypher: list[str] | None = None
) -> ToolResult:
    """Triage from an issue's text, so an issue that isn't in this graph (a new sandbox issue,
    triaged against the FalkorDB graph) works the same way. `issue` needs key, title, body,
    state, url, repo and author; `repo` is the repo whose code the issue is about."""
    cypher = cypher or []
    args = {"issue": issue["key"], "limit": limit}
    evidence = EvidenceBuilder()
    me = evidence.node("Issue", issue["key"], title=issue["title"], url=issue["url"])

    # 1. Similar issues.
    similar: list[dict[str, Any]] = []
    query = "|".join(keywords(issue["title"] or "")[:MAX_QUERY_WORDS])
    if query:
        pool = as_dicts(
            graph.ro_query(SIMILAR, {"query": query, "key": issue["key"], "pool": SIMILAR_POOL})
        )
        wanted = keyword_stems(issue["title"] or "")
        for row in pool:
            # Title coverage decides "likely duplicate"; the body only helps the ordering.
            row["match"] = round(coverage(wanted, row["title"]), 2)
            row["_rank"] = row["match"] + 0.5 * coverage(wanted, f"{row['title']} {row['body']}")
        pool.sort(key=lambda r: (-r["_rank"], r["repo"] != issue["repo"], -r["score"]))
        similar = pool[:VOTERS]
        cypher.append(SIMILAR.strip())

    # 2. Component votes.
    votes: dict[str, dict[str, Any]] = {}

    def vote(component: str, name: str, weight: float, via: str) -> dict[str, Any]:
        entry = votes.setdefault(
            component, {"key": component, "name": name, "votes": 0.0, "via": []}
        )
        entry["votes"] += weight
        if via not in entry["via"]:
            entry["via"].append(via)
        return entry

    weights = {s["key"]: max(s["_rank"], 0.1) for s in similar}
    weights[issue["key"]] = OWN_FIX_WEIGHT
    fixes = [
        row
        for row in as_dicts(graph.ro_query(FIX_COMPONENTS, {"issues": list(weights)}))
        # Only the issue's own repo can be labelled; infrastructure folders never vote.
        if row["component"].startswith(f"{issue['repo']}:") and not _is_infra(row["component"])
    ]
    cypher.append(FIX_COMPONENTS.strip())
    # A PR touching ten Components says little about each: split its vote (1/sqrt(n)).
    spread: dict[str, set[str]] = {}
    for row in fixes:
        spread.setdefault(row["pr"], set()).add(row["component"])
    seen: set[tuple[str, str]] = set()
    for row in fixes:
        if (row["issue"], row["component"]) in seen:
            continue  # one vote per issue per Component, however many files the PR touched
        seen.add((row["issue"], row["component"]))
        share = weights[row["issue"]] / len(spread[row["pr"]]) ** 0.5
        vote(row["component"], row["name"], share, row["issue"])
        issue_id = me if row["issue"] == issue["key"] else f"Issue:{row['issue']}"
        pr_id = evidence.node("PullRequest", row["pr"], title=row["pr_title"], url=row["pr_url"])
        file_id = evidence.node("File", row["file"], title=row["path"])
        component_id = evidence.node("Component", row["component"], title=row["name"])
        evidence.edge(pr_id, "FIXES", issue_id)
        evidence.edge(pr_id, "MODIFIES", file_id)
        evidence.edge(file_id, "IN_COMPONENT", component_id)

    paths = mentioned_paths(f"{issue['title']}\n{issue['body'] or ''}")
    mentions = (
        as_dicts(graph.ro_query(MENTIONED_FILES, {"paths": paths, "repo": issue["repo"]}))
        if paths
        else []
    )
    if paths:
        cypher.append(MENTIONED_FILES.strip())
    for row in mentions:
        vote(row["component"], row["name"], MENTION_WEIGHT, row["path"])
        file_id = evidence.node("File", row["file"], title=row["path"])
        component_id = evidence.node("Component", row["component"], title=row["name"])
        evidence.edge(file_id, "IN_COMPONENT", component_id)

    # Titles only: issue templates fill bodies with generic words ("error", "description").
    issue_words = keyword_stems(issue["title"] or "")
    repo_components = [
        row
        for row in as_dicts(graph.ro_query(REPO_COMPONENTS, {"repo": issue["repo"]}))
        if not _is_infra(row["key"])
    ]
    path_words = {row["key"]: _path_words(row["path"]) for row in repo_components}
    # "graph" is in most FalkorDB paths, so it says nothing; only distinctive words vote.
    frequency: dict[str, int] = {}
    for words in path_words.values():
        for word in words:
            frequency[word] = frequency.get(word, 0) + 1
    common = max(2, COMMON_WORD_SHARE * len(repo_components))
    for row in repo_components:
        matched = {w for w in issue_words & path_words[row["key"]] if frequency[w] <= common}
        if matched:
            vote(
                row["key"],
                row["name"],
                NAME_WEIGHT * len(matched),
                "name: " + ", ".join(sorted(matched)),
            )
            evidence.node("Component", row["key"], title=row["name"])
    cypher.append(REPO_COMPONENTS.strip())

    # Similar issues go on the path even when no fixing PR links them to a Component yet.
    for s in similar:
        evidence.node("Issue", s["key"], title=s["title"], url=s["url"])
    similar = similar[:limit]

    ranked = sorted(votes.values(), key=lambda v: -v["votes"])[:3]

    # 3. Experts for the top Component.
    experts: list[dict[str, Any]] = []
    if ranked:
        found_experts = experts_for(graph, ExpertsForArgs(component=ranked[0]["key"], limit=4))
        cypher.extend(q for q in found_experts.cypher if q not in cypher)
        experts = [e for e in found_experts.rows if e["login"] != issue["author"]][:3]
        keep = {f"Person:{e['login']}" for e in experts}
        _merge(evidence, found_experts.evidence, keep)

    row = {
        "issue": {k: issue[k] for k in ("title", "state", "url", "repo", "author")}
        | {"key": issue["key"]},
        "similar": [
            {k: s[k] for k in ("key", "title", "state", "url", "repo", "match", "fixed_by")}
            | {"likely_duplicate": s["match"] >= DUPLICATE_COVERAGE}
            for s in similar
        ],
        "components": [
            {
                "key": v["key"],
                "name": v["name"],
                "votes": round(v["votes"], 2),
                "strength": _strength(v["votes"]),
                "via": v["via"][:5],
            }
            for v in ranked
        ],
        "experts": [
            {k: e[k] for k in ("login", "score", "authored_prs", "reviewed_prs", "comments")}
            for e in experts
        ],
        "mentioned_files": sorted({m["path"] for m in mentions}),
    }
    return ToolResult(
        tool="triage_candidates",
        args=args,
        rows=[row],
        evidence=evidence.build(),
        cypher=cypher,
    )


def _strength(votes: float) -> str:
    """How much the graph backs a Component pick, so a reply can hedge when it should."""
    return "strong" if votes >= STRONG_VOTES else "moderate" if votes >= MODERATE_VOTES else "weak"


def _is_infra(component_key: str) -> bool:
    path = component_key.split(":", 1)[-1]
    return any(part in _INFRA or part.startswith(".") for part in path.split("/"))


def _path_words(path: str | None) -> set[str]:
    return keyword_stems(re.sub(r"[/_.-]", " ", path or ""))


def _merge(evidence: EvidenceBuilder, path: EvidencePath, people: set[str]) -> None:
    """Add an experts_for path, keeping only the chosen people and what hangs off them."""
    reachable = set(people)
    for edge in path.edges:  # Person -> PR -> File -> Component, in that order
        if edge.source in reachable:
            reachable.add(edge.target)
    for node in path.nodes:
        if node.id in reachable:
            label, key = node.id.split(":", 1)
            evidence.node(label, key, title=node.title, url=node.url)
    for edge in path.edges:
        if edge.source in reachable:
            evidence.edge(edge.source, edge.type, edge.target)
