"""decision_trail and SUPERSEDES linking on the fixture graph.

Setup: an older decision on PR 103 (affects falkordb/) and a newer one on PR 101 (affects
falkordb/, evidenced by review comment rc:21). PR 101's thread links to PR 103's only after
we add a REFERENCES edge, so SUPERSEDES must appear only then.
"""

import pytest

from aevion.extract.extractor import DecisionRec
from aevion.extract.loader import link_supersedes, load_decisions
from aevion.graph.client import OrgGraph
from aevion.tools.decisions import DecisionTrailArgs, decision_trail, fulltext_query
from aevion.tools.evidence import missing_edges

pytestmark = pytest.mark.integration

REPO = "FalkorDB/falkordb-py"
DAY = 86_400_000


def _decision(
    id_: str, thread: str, summary: str, at: int, evidence: tuple[str, ...] = ()
) -> DecisionRec:
    return DecisionRec(
        id=id_,
        thread_key=thread,
        thread_label="PullRequest",
        summary=summary,
        rationale="Queries could hang forever on an unreachable server",
        alternatives=("a global client timeout",),
        decided_at=at,
        confidence=0.9,
        model="test",
        source_url="u",
        made_by=("alice",),
        components=(f"{REPO}:falkordb",),
        evidence=evidence,
    )


@pytest.fixture
def with_decisions(fixture_graph: OrgGraph) -> OrgGraph:
    # PR 103 normally modifies docs only; let it touch falkordb/ too for this scenario.
    fixture_graph.query(
        "MATCH (pr:PullRequest {number: 103}), (f:File {path: 'falkordb/asyncio/graph.py'}) "
        "MERGE (pr)-[:MODIFIES]->(f)"
    )
    load_decisions(
        fixture_graph,
        [
            _decision(
                "dec:old", f"{REPO}#103", "Rely on server-side query timeouts only", 1_000 * DAY
            ),
            _decision(
                "dec:new",
                f"{REPO}#101",
                "Async queries take an explicit client timeout",
                2_000 * DAY,
                ("rc:21",),
            ),
        ],
    )
    return fixture_graph


def test_fulltext_query_drops_stopwords_and_punctuation() -> None:
    assert fulltext_query("Why did we add a timeout (for async)?") == "add|timeout|async"
    assert fulltext_query("why is it?") is None


def test_finds_a_decision_by_topic_with_its_trail(with_decisions: OrgGraph) -> None:
    result = decision_trail(
        with_decisions, DecisionTrailArgs(topic="client timeouts for async queries")
    )
    # Both decisions match the words; full-text score decides order, so find ours by id.
    top = next(r for r in result.rows if r["id"] == "dec:new")
    assert top["decided_in"]["key"] == f"{REPO}#101"
    assert top["fixed_issues"][0]["key"] == f"{REPO}#90"
    assert top["made_by"] == ["alice"]
    assert top["quotes"][0]["author"] == "bob"
    assert missing_edges(with_decisions, result.evidence) == []


def test_supersedes_needs_a_thread_link(with_decisions: OrgGraph) -> None:
    link_supersedes(with_decisions)
    unlinked = decision_trail(with_decisions, DecisionTrailArgs(topic="client timeout"))
    assert unlinked.rows[0]["replaces"] == []  # same component, but threads not linked

    with_decisions.query(
        "MATCH (a:PullRequest {number: 101}), (b:PullRequest {number: 103}) "
        "MERGE (a)-[:REFERENCES]->(b)"
    )
    for _ in range(2):  # idempotent
        link_supersedes(with_decisions)
    linked = decision_trail(with_decisions, DecisionTrailArgs(topic="client timeout"))
    new = next(r for r in linked.rows if r["id"] == "dec:new")
    assert [d["id"] for d in new["replaces"]] == ["dec:old"]
    assert {e.type for e in linked.evidence.edges} >= {"SUPERSEDES", "DECIDED_IN", "EVIDENCED_BY"}
    assert missing_edges(with_decisions, linked.evidence) == []
    old = decision_trail(with_decisions, DecisionTrailArgs(topic="server-side timeouts"))
    assert old.rows[0]["replaced_by"][0]["id"] == "dec:new"


def test_component_only_lists_newest_first(with_decisions: OrgGraph) -> None:
    result = decision_trail(with_decisions, DecisionTrailArgs(component="falkordb", repo=REPO))
    assert [r["id"] for r in result.rows] == ["dec:new", "dec:old"]


def test_needs_a_topic_or_component() -> None:
    with pytest.raises(ValueError):
        DecisionTrailArgs(topic="  ")


def test_nothing_matches(with_decisions: OrgGraph) -> None:
    assert (
        decision_trail(with_decisions, DecisionTrailArgs(topic="kubernetes helm chart")).rows == []
    )
