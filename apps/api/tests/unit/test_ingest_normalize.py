"""Normalising GitHub pull request pages into loader records."""

from pathlib import Path
from typing import Any

import pytest

from aevion.config import REPO_ROOT
from aevion.ingest.components import component_path, is_doc
from aevion.ingest.normalize import Batch, person_from, pull_request_from, to_epoch_ms
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
    assert sorted(people) == ["alice", "bob", "coderabbitai", "dependabot"]
    assert people["dependabot"].is_bot and people["coderabbitai"].is_bot


def test_org_config_loads_demo_dataset() -> None:
    config = load_org_config(Path(REPO_ROOT / "config" / "orgs" / "falkordb.toml"))
    assert config.org == "FalkorDB"
    assert len(config.repos) == 9
    assert config.repo("falkordb-py").component_depth == 1
    assert config.repo("FalkorDB").component_depth == 2
