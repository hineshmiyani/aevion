"""Normalising GitHub pull request pages into loader records."""

from pathlib import Path
from typing import Any

import pytest

from aevion.config import REPO_ROOT
from aevion.ingest.components import component_path, is_doc
from aevion.ingest.normalize import Batch, issue_from, person_from, pull_request_from, to_epoch_ms
from aevion.ingest.org_config import load_org_config

BOTS = frozenset({"dependabot"})
REPO = "FalkorDB/falkordb-py"


def _normalise(page: dict[str, Any], depth: int = 1) -> Batch:
    batch = Batch()
    for node in page["pullRequests"]["nodes"]:
        pull_request_from(node, REPO, depth, BOTS, batch)
    return batch


@pytest.mark.parametrize(
    ("path", "depth", "expected"),
    [
        ("src/execution_plan/ops/op_filter.c", 2, "src/execution_plan"),
        ("falkordb/asyncio/graph.py", 1, "falkordb"),
        ("falkordb/graph.py", 2, "falkordb"),
        ("README.md", 2, "(root)"),
    ],
)
def test_component_path(path: str, depth: int, expected: str) -> None:
    assert component_path(path, depth) == expected


def test_is_doc() -> None:
    assert is_doc("README.md") and is_doc("docs/setup/index.html")
    assert not is_doc("falkordb/graph.py")


def test_to_epoch_ms() -> None:
    assert to_epoch_ms("1970-01-01T00:00:01Z") == 1000
    assert to_epoch_ms(None) is None


def test_bots_are_flagged_by_type_suffix_and_config() -> None:
    assert person_from({"__typename": "Bot", "login": "coderabbitai"}, frozenset()).is_bot  # type: ignore[union-attr]
    assert person_from({"__typename": "User", "login": "ci[bot]"}, frozenset()).is_bot  # type: ignore[union-attr]
    assert person_from({"__typename": "User", "login": "Dependabot"}, BOTS).is_bot  # type: ignore[union-attr]
    assert not person_from({"__typename": "User", "login": "alice"}, BOTS).is_bot  # type: ignore[union-attr]


def test_deleted_author_is_skipped(pr_page: dict[str, Any]) -> None:
    batch = _normalise(pr_page)
    ghost_pr = next(pr for pr in batch.pull_requests if pr.number == 103)
    assert ghost_pr.author is None


def test_pull_request_fields(pr_page: dict[str, Any]) -> None:
    pr = _normalise(pr_page).pull_requests[0]
    assert pr.key == "FalkorDB/falkordb-py#101"
    assert pr.author == "alice"
    assert pr.merged_at == to_epoch_ms("2026-09-03T12:00:00Z")
    assert [f.component_key for f in pr.files] == [
        "FalkorDB/falkordb-py:falkordb",
        "FalkorDB/falkordb-py:tests",
        "FalkorDB/falkordb-py:(root)",
    ]


def test_one_review_per_person_keeps_latest_state(pr_page: dict[str, Any]) -> None:
    pr = _normalise(pr_page).pull_requests[0]
    states = {r.login: r.state for r in pr.reviews}
    assert states["bob"] == "APPROVED"  # COMMENTED earlier, APPROVED later
    assert set(states) == {"bob", "alice", "coderabbitai"}


def test_people_are_deduplicated(pr_page: dict[str, Any]) -> None:
    people = _normalise(pr_page).people
    assert sorted(people) == ["alice", "bob", "carol", "coderabbitai", "dependabot"]
    assert people["dependabot"].is_bot and people["coderabbitai"].is_bot


def test_org_config_loads_demo_dataset() -> None:
    config = load_org_config(Path(REPO_ROOT / "config" / "orgs" / "falkordb.toml"))
    assert config.org == "FalkorDB"
    assert len(config.repos) == 9
    assert config.repo("falkordb-py").component_depth == 1
    assert config.repo("FalkorDB").component_depth == 2


def test_pull_request_references_and_fixes(pr_page: dict[str, Any]) -> None:
    pr = _normalise(pr_page).pull_requests[0]
    assert pr.fix_keys == (f"{REPO}#90",)  # body "Fixes #90" + closingIssuesReferences
    # from a human comment; the bot comment's "#999" and the bot review's "#77" are ignored
    assert pr.ref_keys == ("FalkorDB/FalkorDB#1200", f"{REPO}#95")
    assert pr.labels == (f"{REPO}:enhancement",)


def test_comments_skip_bots_and_empty_reviews(pr_page: dict[str, Any]) -> None:
    comments = {c.id: c for c in _normalise(pr_page).comments}
    assert sorted(comments) == ["ic:501", "rc:21", "rv:11"]
    assert comments["rc:21"].kind == "review_thread"
    assert comments["rc:21"].author == "bob"
    assert {c.thread_key for c in comments.values()} == {f"{REPO}#101"}


def test_issue_normalisation(issue_page: dict[str, Any]) -> None:
    batch = Batch()
    for node in issue_page["issues"]["nodes"]:
        issue_from(node, REPO, BOTS, batch)
    issue = batch.issues[0]
    assert issue.key == f"{REPO}#90"
    assert issue.assignees == ("alice",)
    assert issue.labels == (f"{REPO}:bug",)
    assert issue.ref_keys == ("FalkorDB/FalkorDB#1200", f"{REPO}#101")
    assert batch.issues[2].author is None  # deleted user
    assert batch.issues[2].ref_keys == (f"{REPO}#90",)
    assert [c.id for c in batch.comments] == ["ic:601"]


def test_depth_overrides_use_the_longest_matching_prefix() -> None:
    overrides = {"graphrag_sdk/src/graphrag_sdk": 4, "graphrag_sdk": 2}
    deep = "graphrag_sdk/src/graphrag_sdk/ingestion/structured_pipeline.py"
    assert component_path(deep, 2, overrides) == "graphrag_sdk/src/graphrag_sdk/ingestion"
    assert component_path("graphrag_sdk/tests/test_x.py", 2, overrides) == "graphrag_sdk/tests"
    assert component_path("docs/extraction.mdx", 2, overrides) == "docs"
    # a prefix must match whole directory names, not part of one
    assert (
        component_path("graphrag_sdk_extra/a/b.py", 1, {"graphrag_sdk": 3}) == "graphrag_sdk_extra"
    )


def test_org_config_reads_depth_overrides() -> None:
    config = load_org_config(Path(REPO_ROOT / "config" / "orgs" / "falkordb.toml"))
    assert config.repo("GraphRAG-SDK").depth_overrides["graphrag_sdk/src/graphrag_sdk"] == 4
    assert config.repo("falkordb-py").depth_overrides == {}
