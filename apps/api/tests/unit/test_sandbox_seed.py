"""Seeding: selection, safe copies, idempotency and the allow-list, without touching GitHub."""

import json
import re
from typing import Any

import httpx
import pytest

from aevion.sandbox.seed import copy_body, original_of, pick
from aevion.sandbox.writer import SandboxWriter, WriteNotAllowedError

SANDBOX = "hineshmiyani/aevion-sandbox"
ALLOWED = frozenset({SANDBOX})


def _issue(key: str, at: int, body: str = "A real description of the problem.") -> dict[str, Any]:
    return {
        "key": key,
        "title": f"Issue {key}",
        "body": body,
        "created_at": at,
        "repo": key.split("#")[0],
    }


def test_pick_spreads_across_repos() -> None:
    big = [_issue(f"o/big#{n}", 1000 - n) for n in range(100)]
    small = [_issue(f"o/small#{n}", 500 - n) for n in range(4)]
    chosen = pick(big + small, 10)
    repos = [c["repo"] for c in chosen]
    assert len(chosen) == 10 and "o/small" in repos and repos.count("o/big") >= 6


def test_copy_is_labelled_safe_and_marked() -> None:
    issue = _issue("FalkorDB/FalkorDB#77", 1_760_000_000_000, "Broke in #70, cc @swilly22")
    body = copy_body(issue, SANDBOX)
    assert "not a real report" in body and "`FalkorDB/FalkorDB#77`" in body
    assert "`FalkorDB/FalkorDB#70`" in body and "[swilly22](https://github.com/swilly22)" in body
    prose = re.sub(r"`[^`]*`", "", body)
    assert "@" not in prose and "#7" not in prose  # nothing GitHub could turn into a reference
    assert original_of({"body": body}) == "FalkorDB/FalkorDB#77"


def test_writer_refuses_repos_outside_the_allow_list() -> None:
    with pytest.raises(WriteNotAllowedError):
        SandboxWriter("token", "FalkorDB/FalkorDB", ALLOWED)
    with pytest.raises(WriteNotAllowedError):
        SandboxWriter("", SANDBOX, ALLOWED)


def test_writer_only_calls_the_sandbox() -> None:
    calls: list[tuple[str, str, Any]] = []

    def github(request: httpx.Request) -> httpx.Response:
        calls.append(
            (request.method, request.url.path, request.content and json.loads(request.content))
        )
        if request.method == "GET" and not request.url.path.endswith("/issues"):
            return httpx.Response(404)  # probing past the list: nothing newer
        if request.method == "GET":
            return httpx.Response(
                200, json=[{"number": 1, "body": "<!-- aevion-copy-of: a/b issue 1 -->"}]
            )
        return httpx.Response(201, json={"number": 2})

    writer = SandboxWriter("t", SANDBOX, ALLOWED, transport=httpx.MockTransport(github), pause_s=0)
    assert [original_of(i) for i in writer.issues()] == ["a/b#1"]
    writer.create_issue("Title", "Body")
    assert all(path.startswith(f"/repos/{SANDBOX}/") for _, path, _ in calls)
    assert calls[-1][0] == "POST" and calls[-1][2] == {"title": "Title", "body": "Body"}


def test_issues_the_list_has_not_caught_up_with_are_still_found() -> None:
    def github(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/issues"):  # the lagging list knows only issue 1
            return httpx.Response(200, json=[{"number": 1, "body": ""}])
        number = int(request.url.path.rsplit("/", 1)[1])
        if number <= 3:  # but 2 and 3 exist
            return httpx.Response(200, json={"number": number, "body": f"n{number}"})
        return httpx.Response(404)

    writer = SandboxWriter("t", SANDBOX, ALLOWED, transport=httpx.MockTransport(github), pause_s=0)
    assert [i["number"] for i in writer.issues()] == [1, 2, 3]
