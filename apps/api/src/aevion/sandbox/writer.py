"""The only code in Aevion that writes to GitHub (ADR-0005).

It is built for one repo, refuses to exist for a repo outside the allow-list, and uses the
sandbox token, a fine-grained token that GitHub itself limits to that repo. Two locks, so a
bug in one still can't touch FalkorDB's repos.
"""

import time
from typing import Any

import httpx

API = "https://api.github.com"
WRITE_PAUSE_S = 1.0  # GitHub's secondary limits punish bursts of content creation
MAX_PROBE = 100  # numbers to check past the list's highest, for issues it doesn't show yet


class WriteNotAllowedError(Exception):
    """A write was attempted outside the allow-list."""


class SandboxWriter:
    def __init__(
        self,
        token: str,
        repo: str,
        allowed_repos: frozenset[str],
        *,
        transport: httpx.BaseTransport | None = None,
        pause_s: float = WRITE_PAUSE_S,
    ) -> None:
        if repo not in allowed_repos:
            raise WriteNotAllowedError(f"{repo} is not an allowed sandbox repo")
        if not token:
            raise WriteNotAllowedError("SANDBOX_GITHUB_TOKEN is not set")
        self.repo = repo
        self._pause_s = pause_s
        self._http = httpx.Client(
            base_url=f"{API}/repos/{repo}",
            transport=transport,
            timeout=20,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "aevion-triage",
            },
        )

    def issues(self) -> list[dict[str, Any]]:
        """Every issue in the sandbox (not PRs), open and closed.

        The list endpoint lags a few seconds behind writes, so issues just created can be
        missing from it. Issue numbers are sequential and fetching one by number is consistent,
        so after listing we probe the numbers above the highest seen until GitHub says 404.
        """
        found: list[dict[str, Any]] = []
        page = 1
        while True:
            batch = self._get("/issues", {"state": "all", "per_page": 100, "page": page})
            found += [i for i in batch if "pull_request" not in i]
            if len(batch) < 100:
                break
            page += 1
        number = max((i["number"] for i in found), default=0)
        for _ in range(MAX_PROBE):
            number += 1
            response = self._http.get(f"/issues/{number}")
            if response.status_code == 404:
                break
            response.raise_for_status()
            item = response.json()
            if "pull_request" not in item:
                found.append(item)
        return found

    def create_issue(self, title: str, body: str) -> dict[str, Any]:
        return self._write("POST", "/issues", {"title": title, "body": body})

    def ensure_label(self, name: str, color: str, description: str = "") -> None:
        response = self._http.get(f"/labels/{name}")
        if response.status_code == 404:
            self._write(
                "POST", "/labels", {"name": name, "color": color, "description": description}
            )
        else:
            response.raise_for_status()

    def add_labels(self, number: int, labels: list[str]) -> None:
        self._write("POST", f"/issues/{number}/labels", {"labels": labels})

    def is_collaborator(self, login: str) -> bool:
        return self._http.get(f"/collaborators/{login}").status_code == 204

    def assign(self, number: int, login: str) -> None:
        self._write("POST", f"/issues/{number}/assignees", {"assignees": [login]})

    def close_issue(self, number: int, reason: str = "not_planned") -> None:
        self._write("PATCH", f"/issues/{number}", {"state": "closed", "state_reason": reason})

    def comment(self, number: int, body: str) -> dict[str, Any]:
        return self._write("POST", f"/issues/{number}/comments", {"body": body})

    def close(self) -> None:
        self._http.close()

    def _get(self, path: str, params: dict[str, Any]) -> Any:
        response = self._http.get(path, params=params)
        response.raise_for_status()
        return response.json()

    def _write(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._http.request(method, path, json=payload)
        response.raise_for_status()
        time.sleep(self._pause_s)
        body: dict[str, Any] = response.json()
        return body
