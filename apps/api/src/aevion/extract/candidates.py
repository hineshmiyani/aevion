"""Pick the threads worth sending to the model (graph-model.md, "Decision-candidate filter").

A thread is a candidate if it is a merged PR with real review discussion (3+ review
comments) or a linked issue, a closed issue with 3+ comments, or a merged PR that changes
docs. Everything else stays deterministic structure with no LLM cost.
"""

from dataclasses import dataclass, field
from typing import Any

from aevion.graph.client import OrgGraph
from aevion.tools.scope import as_dicts

MIN_COMMENTS = 3
MAX_COMMENTS_PER_THREAD = 12

PR_CANDIDATES = """
MATCH (pr:PullRequest)-[:IN_REPO]->(r:Repo)
WHERE pr.merged_at IS NOT NULL AND ($repo IS NULL OR r.full_name = $repo)
OPTIONAL MATCH (c:Comment)-[:ON]->(pr) WHERE c.kind IN ['review', 'review_thread']
WITH pr, count(c) AS review_comments
OPTIONAL MATCH (pr)-[:FIXES]->(i:Issue)
WITH pr, review_comments, count(i) AS fixed
OPTIONAL MATCH (pr)-[:MODIFIES]->(f:File {is_doc: true})
WITH pr, review_comments, fixed, count(f) AS doc_files
WHERE review_comments >= $min_comments OR fixed > 0 OR doc_files > 0
RETURN pr.key AS key
ORDER BY pr.merged_at DESC
"""

ISSUE_CANDIDATES = """
MATCH (i:Issue)-[:IN_REPO]->(r:Repo)
WHERE i.state = 'CLOSED' AND ($repo IS NULL OR r.full_name = $repo)
MATCH (c:Comment)-[:ON]->(i)
WITH i, count(c) AS comments
WHERE comments >= $min_comments
RETURN i.key AS key
ORDER BY i.closed_at DESC
"""

# Label-specific so every lookup uses the key index.
_THREAD = """
MATCH (t:{label} {{key: $key}})
OPTIONAL MATCH (a:Person)-[:AUTHORED]->(t)
RETURN t.title AS title, t.body_excerpt AS body, t.url AS url,
       coalesce(t.merged_at, t.closed_at) AS decided_at, a.login AS author
"""

_THREAD_COMMENTS = """
MATCH (p:Person)-[:AUTHORED]->(c:Comment)-[:ON]->(t:{label} {{key: $key}})
RETURN c.id AS id, c.kind AS kind, c.excerpt AS text, p.login AS author
ORDER BY c.created_at
LIMIT $limit
"""

# Components the work touched: the PR's own files, or the files of PRs that fixed the issue.
_THREAD_COMPONENTS = {
    "PullRequest": """
MATCH (pr:PullRequest {key: $key})-[:MODIFIES]->(:File)-[:IN_COMPONENT]->(c:Component)
WITH c, count(*) AS files
RETURN c.key AS key ORDER BY files DESC LIMIT 6
""",
    "Issue": """
MATCH (:Issue {key: $key})<-[:FIXES]-(:PullRequest)-[:MODIFIES]->(:File)
      -[:IN_COMPONENT]->(c:Component)
WITH c, count(*) AS files
RETURN c.key AS key ORDER BY files DESC LIMIT 6
""",
}


@dataclass
class Thread:
    key: str
    label: str
    title: str
    body: str
    url: str
    decided_at: int | None
    author: str | None
    comments: list[dict[str, Any]] = field(default_factory=list)
    components: list[str] = field(default_factory=list)

    @property
    def participants(self) -> set[str]:
        people = {c["author"] for c in self.comments}
        return people | ({self.author} if self.author else set())

    @property
    def kind(self) -> str:
        return "Pull request" if self.label == "PullRequest" else "Issue"

    def as_prompt_text(self) -> str:
        """The thread as the model sees it. Comment ids let it cite evidence."""
        lines = [
            f"{self.kind} {self.key}: {self.title}",
            f"Opened by: {self.author or 'unknown'}",
            f"Components touched: {', '.join(self.components) or 'none recorded'}",
            "",
            "Description:",
            self.body.strip() or "(empty)",
            "",
            "Discussion:",
        ]
        for c in self.comments:
            lines.append(f"[{c['id']}] {c['author']} ({c['kind']}): {c['text'].strip()}")
        if not self.comments:
            lines.append("(no comments)")
        return "\n".join(lines)


def candidates(graph: OrgGraph, repo: str | None = None) -> list[tuple[str, str]]:
    """(key, label) of every candidate thread, newest first within PRs then issues."""
    params = {"repo": repo, "min_comments": MIN_COMMENTS}
    prs = [(row[0], "PullRequest") for row in graph.ro_query(PR_CANDIDATES, params).rows]
    issues = [(row[0], "Issue") for row in graph.ro_query(ISSUE_CANDIDATES, params).rows]
    return prs + issues


def load_thread(graph: OrgGraph, key: str, label: str) -> Thread:
    head = as_dicts(graph.ro_query(_THREAD.format(label=label), {"key": key}))[0]
    comments = as_dicts(
        graph.ro_query(
            _THREAD_COMMENTS.format(label=label), {"key": key, "limit": MAX_COMMENTS_PER_THREAD}
        )
    )
    components = [row[0] for row in graph.ro_query(_THREAD_COMPONENTS[label], {"key": key}).rows]
    return Thread(
        key=key,
        label=label,
        title=head["title"] or "",
        body=head["body"] or "",
        url=head["url"],
        decided_at=head["decided_at"],
        author=head["author"],
        comments=comments,
        components=components,
    )
