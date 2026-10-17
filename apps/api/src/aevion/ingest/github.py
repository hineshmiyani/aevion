"""GitHub GraphQL client for public data, with retries and an optional raw-response cache.

The cache (data/raw/, git-ignored) lets a full re-ingestion skip the network while we
iterate on normalisation and the graph model (plan risk: GitHub rate limits).
"""

import hashlib
import json
import time
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

GRAPHQL_URL = "https://api.github.com/graphql"
MAX_ATTEMPTS = 5

_ACTOR = "author { __typename login avatarUrl }"
_COMMENTS = f"comments(first: 50) {{ nodes {{ databaseId body url createdAt {_ACTOR} }} }}"
_LABELS = "labels(first: 20) { nodes { name color } }"

PULL_REQUESTS_QUERY = f"""
query($owner: String!, $name: String!, $after: String) {{
  repository(owner: $owner, name: $name) {{
    nameWithOwner url stargazerCount
    defaultBranchRef {{ name }}
    pullRequests(first: 25, after: $after, orderBy: {{field: UPDATED_AT, direction: DESC}}) {{
      pageInfo {{ hasNextPage endCursor }}
      nodes {{
        number title body url state createdAt updatedAt mergedAt closedAt additions deletions
        {_ACTOR}
        {_LABELS}
        {_COMMENTS}
        closingIssuesReferences(first: 10) {{ nodes {{ number repository {{ nameWithOwner }} }} }}
        reviews(first: 50) {{ nodes {{
          databaseId body url state submittedAt {_ACTOR}
          comments(first: 20) {{ nodes {{ databaseId body url createdAt }} }}
        }} }}
        files(first: 100) {{ nodes {{ path additions deletions }} }}
      }}
    }}
  }}
}}
"""

ISSUES_QUERY = f"""
query($owner: String!, $name: String!, $after: String, $since: DateTime!) {{
  repository(owner: $owner, name: $name) {{
    nameWithOwner url stargazerCount
    defaultBranchRef {{ name }}
    issues(first: 50, after: $after, orderBy: {{field: UPDATED_AT, direction: DESC}},
           filterBy: {{since: $since}}) {{
      pageInfo {{ hasNextPage endCursor }}
      nodes {{
        number title body url state createdAt updatedAt closedAt
        {_ACTOR}
        {_LABELS}
        assignees(first: 5) {{ nodes {{ login avatarUrl }} }}
        {_COMMENTS}
      }}
    }}
  }}
}}
"""


CODEOWNERS_HISTORY_QUERY = """
query($owner: String!, $name: String!, $path: String!, $expression: String!) {
  repository(owner: $owner, name: $name) {
    head: object(expression: $expression) { ... on Blob { text } }
    defaultBranchRef { target { ... on Commit {
      history(path: $path, first: 20) { nodes { oid committedDate } }
    } } }
  }
}
"""

BLOB_QUERY = """
query($owner: String!, $name: String!, $expression: String!) {
  repository(owner: $owner, name: $name) {
    object(expression: $expression) { ... on Blob { text } }
  }
}
"""

RELEASES_QUERY = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    releases(first: 50, orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes { tagName name url publishedAt description }
    }
  }
}
"""


class GitHubError(Exception):
    pass


class GitHubClient:
    def __init__(self, token: str, cache_dir: Path | None = None, timeout: float = 60.0) -> None:
        self._http = httpx.Client(
            headers={"Authorization": f"Bearer {token}", "User-Agent": "aevion-ingest"},
            timeout=timeout,
        )
        self._cache_dir = cache_dir

    def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        cached = self._cache_path(query, variables)
        if cached and cached.exists():
            data: dict[str, Any] = json.loads(cached.read_text())
            return data

        for attempt in range(1, MAX_ATTEMPTS + 1):
            response = self._http.post(GRAPHQL_URL, json={"query": query, "variables": variables})
            if response.status_code in (502, 503, 504) or _is_rate_limited(response):
                time.sleep(min(60, 2**attempt))
                continue
            response.raise_for_status()
            payload = response.json()
            if payload.get("errors"):
                raise GitHubError(json.dumps(payload["errors"])[:500])
            data = payload["data"]
            if cached:
                cached.parent.mkdir(parents=True, exist_ok=True)
                cached.write_text(json.dumps(data))
            return data
        raise GitHubError(f"GitHub GraphQL failed after {MAX_ATTEMPTS} attempts")

    def pull_request_pages(
        self, owner: str, name: str, since: datetime
    ) -> Iterator[dict[str, Any]]:
        """Yield `repository` payloads, newest-updated first, until PRs are older than `since`."""
        after: str | None = None
        while True:
            repository = self.graphql(
                PULL_REQUESTS_QUERY, {"owner": owner, "name": name, "after": after}
            )["repository"]
            connection = repository["pullRequests"]
            fresh = [pr for pr in connection["nodes"] if _updated_after(pr, since)]
            yield {**repository, "pullRequests": {**connection, "nodes": fresh}}
            if len(fresh) < len(connection["nodes"]) or not connection["pageInfo"]["hasNextPage"]:
                return
            after = connection["pageInfo"]["endCursor"]

    def issue_pages(self, owner: str, name: str, since: datetime) -> Iterator[dict[str, Any]]:
        """Yield `repository` payloads of issues updated since `since` (GitHub filters)."""
        after: str | None = None
        since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
        while True:
            repository = self.graphql(
                ISSUES_QUERY, {"owner": owner, "name": name, "after": after, "since": since_iso}
            )["repository"]
            yield repository
            page_info = repository["issues"]["pageInfo"]
            if not page_info["hasNextPage"]:
                return
            after = page_info["endCursor"]

    def codeowners_versions(
        self, owner: str, name: str, paths: tuple[str, ...]
    ) -> list[tuple[str | None, str]]:
        """(committed_at, text) for every version of the first CODEOWNERS file found, oldest
        first. Falls back to the HEAD version alone if GitHub returns no history."""
        for path in paths:
            repo = self.graphql(
                CODEOWNERS_HISTORY_QUERY,
                {"owner": owner, "name": name, "path": path, "expression": f"HEAD:{path}"},
            )["repository"]
            if not repo["head"]:
                continue
            target = (repo.get("defaultBranchRef") or {}).get("target") or {}
            commits = list(reversed(target.get("history", {}).get("nodes", [])))
            versions: list[tuple[str | None, str]] = []
            for commit in commits:
                blob = self.graphql(
                    BLOB_QUERY,
                    {"owner": owner, "name": name, "expression": f"{commit['oid']}:{path}"},
                )["repository"]["object"]
                if blob:  # None at commits that deleted the file
                    versions.append((commit["committedDate"], blob["text"]))
                else:
                    versions.append((commit["committedDate"], ""))
            return versions or [(None, repo["head"]["text"])]
        return []

    def releases(self, owner: str, name: str, since: datetime) -> list[dict[str, Any]]:
        nodes = self.graphql(RELEASES_QUERY, {"owner": owner, "name": name})["repository"][
            "releases"
        ]["nodes"]
        return [r for r in nodes if r.get("publishedAt") and _published_after(r, since)]

    def close(self) -> None:
        self._http.close()

    def _cache_path(self, query: str, variables: dict[str, Any]) -> Path | None:
        if self._cache_dir is None:
            return None
        digest = hashlib.sha256(
            json.dumps([query, variables], sort_keys=True).encode()
        ).hexdigest()[:24]
        return self._cache_dir / f"{digest}.json"


def _updated_after(node: dict[str, Any], since: datetime) -> bool:
    return datetime.fromisoformat(node["updatedAt"].replace("Z", "+00:00")) >= since


def _published_after(node: dict[str, Any], since: datetime) -> bool:
    return datetime.fromisoformat(node["publishedAt"].replace("Z", "+00:00")) >= since


def _is_rate_limited(response: httpx.Response) -> bool:
    if response.status_code not in (403, 429):
        return False
    return (
        response.headers.get("x-ratelimit-remaining") == "0"
        or "rate limit" in response.text.lower()
    )
