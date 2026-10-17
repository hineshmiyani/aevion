"""area_history, related_work and catch_up on the recorded falkordb-py fixture graph.

Fixture facts used below: merged PR 101 (alice, reviewed by bob) touches falkordb/, tests/
and README.md, fixes issue 90 (closed) and references issue 95 (open); issue 90 references
PR 101; issue 96 (open) references issue 90.
"""

from typing import Any

import pytest

from aevion.graph.client import OrgGraph
from aevion.tools.catch_up import CatchUpArgs, catch_up
from aevion.tools.evidence import ToolResult, missing_edges
from aevion.tools.history import AreaHistoryArgs, area_history
from aevion.tools.registry import TOOLS
from aevion.tools.related import RelatedWorkArgs, related_work

pytestmark = pytest.mark.integration

REPO = "FalkorDB/falkordb-py"


def _row(result: ToolResult) -> dict[str, Any]:
    assert len(result.rows) == 1
    return result.rows[0]


def _assert_evidence_is_real(graph: OrgGraph, result: ToolResult) -> None:
    assert result.evidence.edges, "expected an evidence path"
    assert missing_edges(graph, result.evidence) == []


def test_area_history(fixture_graph: OrgGraph) -> None:
    result = area_history(fixture_graph, AreaHistoryArgs(component="falkordb", repo=REPO, days=365))
    row = _row(result)
    assert [pr["key"] for pr in row["recent_prs"]] == [f"{REPO}#101"]  # unmerged PRs excluded
    assert row["recent_prs"][0]["author"] == "alice"
    assert [i["key"] for i in row["open_issues"]] == [f"{REPO}#95"]  # 90 is closed
    assert {p["login"] for p in row["active_people"]} == {"alice", "bob"}  # bot excluded
    _assert_evidence_is_real(fixture_graph, result)


def test_area_history_window_excludes_old_work(fixture_graph: OrgGraph) -> None:
    result = area_history(fixture_graph, AreaHistoryArgs(component="falkordb", repo=REPO, days=1))
    assert _row(result)["recent_prs"] == []


def test_related_work_for_a_pr(fixture_graph: OrgGraph) -> None:
    result = related_work(fixture_graph, RelatedWorkArgs(key=f"{REPO}#101"))
    row = _row(result)
    assert row["item"]["type"] == "PullRequest"
    linked = {(link["key"], link["link"], link["direction"]) for link in row["linked"]}
    assert linked == {
        (f"{REPO}#90", "FIXES", "out"),
        (f"{REPO}#95", "REFERENCES", "out"),
        (f"{REPO}#90", "REFERENCES", "in"),
    }
    assert row["components"] == [f"{REPO}:(root)", f"{REPO}:falkordb", f"{REPO}:tests"]
    _assert_evidence_is_real(fixture_graph, result)


def test_related_work_for_an_issue_uses_its_linked_prs(fixture_graph: OrgGraph) -> None:
    result = related_work(fixture_graph, RelatedWorkArgs(key=f"{REPO}#90"))
    row = _row(result)
    assert row["item"]["type"] == "Issue"
    assert f"{REPO}:falkordb" in row["components"]  # via PR 101, which fixes it
    assert ("FalkorDB/falkordb-py#96", "REFERENCES", "in") in {
        (link["key"], link["link"], link["direction"]) for link in row["linked"]
    }
    _assert_evidence_is_real(fixture_graph, result)


def test_related_work_unknown_key(fixture_graph: OrgGraph) -> None:
    result = related_work(fixture_graph, RelatedWorkArgs(key=f"{REPO}#9999"))
    assert result.rows == []


def test_catch_up_on_a_component(fixture_graph: OrgGraph) -> None:
    result = catch_up(
        fixture_graph, CatchUpArgs(component="falkordb", repo=REPO, since="2026-08-01")
    )
    row = _row(result)
    assert row["merged_prs"] == 1
    assert [h["key"] for h in row["highlights"]] == [f"{REPO}#101"]
    assert [i["key"] for i in row["closed_issues"]] == [f"{REPO}#90"]
    assert row["drivers"] == [{"login": "alice", "merged_prs": 1}]
    _assert_evidence_is_real(fixture_graph, result)


def test_catch_up_on_a_repo_and_after_the_work(fixture_graph: OrgGraph) -> None:
    whole_repo = catch_up(fixture_graph, CatchUpArgs(repo=REPO, since="2026-08-01"))
    assert _row(whole_repo)["merged_prs"] == 1
    later = catch_up(fixture_graph, CatchUpArgs(repo=REPO, since="2026-10-01"))
    assert _row(later)["merged_prs"] == 0


def test_catch_up_needs_a_scope() -> None:
    with pytest.raises(ValueError):
        CatchUpArgs(since="2026-10-01")


def test_registry_exposes_four_tools() -> None:
    assert list(TOOLS) == ["experts_for", "area_history", "related_work", "catch_up"]


def test_area_history_lists_each_open_issue_once(fixture_graph: OrgGraph) -> None:
    # A second PR in the same component that also references open issue 95.
    fixture_graph.query(
        """
        MATCH (f:File {key: 'FalkorDB/falkordb-py:falkordb/asyncio/graph.py'}),
              (i:Issue {key: 'FalkorDB/falkordb-py#95'}), (r:Repo)
        CREATE (pr:PullRequest {key: 'FalkorDB/falkordb-py#104', number: 104, title: 'Timeout docs',
                                url: 'u104', state: 'MERGED', merged_at: timestamp()}),
               (pr)-[:MODIFIES]->(f), (pr)-[:REFERENCES]->(i), (pr)-[:IN_REPO]->(r)
        """
    )
    result = area_history(fixture_graph, AreaHistoryArgs(component="falkordb", repo=REPO, days=365))
    assert [i["key"] for i in _row(result)["open_issues"]] == [f"{REPO}#95"]
