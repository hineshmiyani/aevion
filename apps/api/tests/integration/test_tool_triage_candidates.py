"""triage_candidates on the fixture graph.

Open issue #95 "Document query timeouts" resembles closed #90 "Async queries hang forever",
which PR 101 fixed by changing falkordb/asyncio/graph.py (plus a test and the README). So the
graph should say: similar to #90, Component falkordb (not tests, not docs), ask alice or bob.
"""

import pytest

from aevion.graph.client import OrgGraph
from aevion.tools.evidence import missing_edges
from aevion.tools.text import stem
from aevion.tools.triage import TriageCandidatesArgs, mentioned_paths, triage_candidates

pytestmark = pytest.mark.integration

REPO = "FalkorDB/falkordb-py"


def test_stem_agrees_with_the_index_on_common_forms() -> None:
    assert stem("queries") == stem("query") == "query"
    assert stem("timeouts") == stem("timeout")
    assert stem("gated") == "gat" and stem("gate") == "gate"  # crude, and that's fine


def test_mentioned_paths() -> None:
    text = "Crash in src/graph/graph.c and op_merge.c, see https://x.io/a.html or v1.2.3"
    assert mentioned_paths(text) == ["src/graph/graph.c", "op_merge.c"]


def test_similar_issue_component_and_experts(fixture_graph: OrgGraph) -> None:
    result = triage_candidates(fixture_graph, TriageCandidatesArgs(issue=f"{REPO}#95"))
    (row,) = result.rows
    assert row["similar"][0]["key"] == f"{REPO}#90"
    assert row["similar"][0]["fixed_by"] == [f"{REPO}#101"]
    components = [c["key"] for c in row["components"]]
    assert components[0] == f"{REPO}:falkordb"
    assert f"{REPO}:tests" not in components  # test folders never vote
    assert {"alice", "bob"} <= {e["login"] for e in row["experts"]}
    assert missing_edges(fixture_graph, result.evidence) == []
    edges = {(e.source, e.type, e.target) for e in result.evidence.edges}
    assert (f"PullRequest:{REPO}#101", "FIXES", f"Issue:{REPO}#90") in edges


def test_a_file_named_in_the_issue_votes_for_its_component(fixture_graph: OrgGraph) -> None:
    fixture_graph.query(
        """
        MATCH (r:Repo {full_name: $repo})
        CREATE (:Issue {key: $key, title: 'Wrong default', state: 'OPEN', url: 'u',
                        body_excerpt: 'The default in asyncio/graph.py looks wrong'})
               -[:IN_REPO]->(r)
        """,
        {"repo": REPO, "key": f"{REPO}#97"},
    )
    result = triage_candidates(fixture_graph, TriageCandidatesArgs(issue=f"{REPO}#97"))
    (row,) = result.rows
    assert row["mentioned_files"] == ["falkordb/asyncio/graph.py"]
    top = row["components"][0]
    assert top["key"] == f"{REPO}:falkordb" and "falkordb/asyncio/graph.py" in top["via"]
    assert missing_edges(fixture_graph, result.evidence) == []


def test_unknown_issue_returns_nothing(fixture_graph: OrgGraph) -> None:
    result = triage_candidates(fixture_graph, TriageCandidatesArgs(issue=f"{REPO}#4040"))
    assert result.rows == [] and result.evidence.nodes == []
