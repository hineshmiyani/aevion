"""Decision extraction end to end on the fixture graph, with the model stubbed."""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from aevion.extract.candidates import candidates, load_thread
from aevion.extract.extractor import TOKEN_BUDGETS, extract_decisions, parse_decisions
from aevion.extract.loader import load_decisions
from aevion.extract.run import run_extraction
from aevion.graph.client import OrgGraph
from aevion.llm.client import ChatResult, Ledger, LLMClient

pytestmark = pytest.mark.integration

REPO = "FalkorDB/falkordb-py"
PR_101 = f"{REPO}#101"

MODEL_REPLY = {
    "decisions": [
        {
            "summary": "Async queries take an explicit timeout and fail instead of hanging",
            "rationale": "Queries hung forever on unreachable servers (issue #90)",
            "alternatives": ["a global client timeout"],
            "made_by": ["alice", "bob", "mallory"],  # mallory never took part
            "components": [f"{REPO}:falkordb", f"{REPO}:not-a-component"],
            "evidence": ["rc:21", "rc:999"],  # rc:999 doesn't exist
            "confidence": 0.82,
        },
        {"summary": "Maybe rename the module someday", "confidence": 0.2},
    ]
}


def _reply(content: str) -> ChatResult:
    return ChatResult(model="anthropic/claude-haiku-5.5", content=content)


def test_candidates_pick_discussed_or_linked_threads(fixture_graph: OrgGraph) -> None:
    picked = candidates(fixture_graph)
    # PR 101: merged and fixes #90. PR 102 isn't merged; PR 103 is a docs PR but not merged;
    # closed issue 90 has only one comment.
    assert picked == [(PR_101, "PullRequest")]


def test_thread_text_carries_comment_ids_and_components(fixture_graph: OrgGraph) -> None:
    thread = load_thread(fixture_graph, PR_101, "PullRequest")
    text = thread.as_prompt_text()
    assert "[rc:21] bob (review_thread): Use asyncio.wait_for here" in text
    assert f"{REPO}:falkordb" in thread.components
    assert thread.participants == {"alice", "bob", "carol"}


def test_model_output_is_validated_against_the_thread(fixture_graph: OrgGraph) -> None:
    thread = load_thread(fixture_graph, PR_101, "PullRequest")
    result = parse_decisions(_reply("Here you go:\n" + json.dumps(MODEL_REPLY)), thread)
    assert result.dropped == 1  # the 0.2-confidence one
    (decision,) = result.decisions
    assert decision.made_by == ("alice", "bob")
    assert decision.components == (f"{REPO}:falkordb",)
    assert decision.evidence == ("rc:21",)
    assert decision.thread_key == PR_101 and decision.id.startswith("dec:")


def test_bad_model_output_is_reported_not_loaded(fixture_graph: OrgGraph) -> None:
    thread = load_thread(fixture_graph, PR_101, "PullRequest")
    assert parse_decisions(_reply("I could not find any"), thread).invalid_json
    assert parse_decisions(_reply('{"decisions": "none"}'), thread).invalid_json
    cut_off = json.dumps(MODEL_REPLY)[:200]  # what a max_tokens cut-off looks like
    assert parse_decisions(_reply(cut_off), thread).invalid_json


def test_one_malformed_decision_does_not_sink_the_rest(fixture_graph: OrgGraph) -> None:
    # Seen in real replies: a valid decision followed by an empty placeholder object.
    thread = load_thread(fixture_graph, PR_101, "PullRequest")
    reply = {"decisions": [MODEL_REPLY["decisions"][0], {"summary": "", "confidence": 0}]}
    result = parse_decisions(_reply(json.dumps(reply)), thread)
    assert not result.invalid_json and len(result.decisions) == 1 and result.dropped == 1


def test_loaded_decision_links_thread_people_component_and_evidence(
    fixture_graph: OrgGraph,
) -> None:
    thread = load_thread(fixture_graph, PR_101, "PullRequest")
    decisions = parse_decisions(_reply(json.dumps(MODEL_REPLY)), thread).decisions
    for _ in range(2):  # idempotent
        load_decisions(fixture_graph, decisions)
    row = fixture_graph.ro_query(
        """
        MATCH (d:Decision)-[:DECIDED_IN]->(t:PullRequest)
        OPTIONAL MATCH (d)-[:MADE_BY]->(p:Person)
        OPTIONAL MATCH (d)-[:AFFECTS]->(c:Component)
        OPTIONAL MATCH (d)-[:EVIDENCED_BY]->(cm:Comment)
        RETURN count(DISTINCT d), t.number, collect(DISTINCT p.login), collect(DISTINCT c.name),
               collect(DISTINCT cm.id)
        """
    ).rows[0]
    assert row[0] == 1 and row[1] == 101
    assert sorted(row[2]) == ["alice", "bob"]
    assert row[3] == ["falkordb"] and row[4] == ["rc:21"]


def test_run_extraction_with_stubbed_model(fixture_graph: OrgGraph, tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []

    def openrouter(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        body = {
            "choices": [{"message": {"content": json.dumps(MODEL_REPLY)}}],
            "usage": {"cost": 0.0001},
        }
        return httpx.Response(200, json=body)

    client = LLMClient(
        "sk-or-test",
        base_url="https://openrouter.test/api/v1",
        cache_dir=tmp_path / "cache",
        ledger=Ledger(tmp_path / "ledger.jsonl"),
        budget_usd=1.0,
        transport=httpx.MockTransport(openrouter),
    )
    report = run_extraction(
        fixture_graph, client, "anthropic/claude-haiku-5.5", None, None, workers=2
    )
    assert (report.threads, report.decisions, report.dropped_low_confidence) == (1, 1, 1)
    assert calls[0]["response_format"] == {"type": "json_object"}
    again = run_extraction(
        fixture_graph, client, "anthropic/claude-haiku-5.5", None, None, workers=2
    )
    assert again.decisions == 1 and len(calls) == 1  # second run served from the LLM cache


def _client(tmp_path: Path, handler: Any) -> LLMClient:
    return LLMClient(
        "sk-or-test",
        base_url="https://openrouter.test/api/v1",
        cache_dir=tmp_path / "cache",
        ledger=Ledger(tmp_path / "ledger.jsonl"),
        budget_usd=1.0,
        transport=httpx.MockTransport(handler),
    )


def test_reply_cut_off_by_max_tokens_is_retried_with_more_room(
    fixture_graph: OrgGraph, tmp_path: Path
) -> None:
    budgets: list[int] = []

    def openrouter(request: httpx.Request) -> httpx.Response:
        budget = json.loads(request.content)["max_tokens"]
        budgets.append(budget)
        if budget == TOKEN_BUDGETS[0]:  # reasoning used the budget; the JSON is cut off
            choice = {
                "message": {"content": json.dumps(MODEL_REPLY)[:120]},
                "finish_reason": "length",
            }
        else:
            choice = {"message": {"content": json.dumps(MODEL_REPLY)}, "finish_reason": "stop"}
        return httpx.Response(200, json={"choices": [choice], "usage": {"cost": 0.0001}})

    thread = load_thread(fixture_graph, PR_101, "PullRequest")
    result = extract_decisions(_client(tmp_path, openrouter), "m", thread)
    assert budgets == list(TOKEN_BUDGETS)
    assert result.retried and not result.truncated and not result.invalid_json
    assert len(result.decisions) == 1


def test_reply_still_cut_off_after_the_retry_is_counted(
    fixture_graph: OrgGraph, tmp_path: Path
) -> None:
    def openrouter(request: httpx.Request) -> httpx.Response:
        choice = {"message": {"content": '{"decisions": [{"summ'}, "finish_reason": "length"}
        return httpx.Response(200, json={"choices": [choice], "usage": {"cost": 0.0001}})

    report = run_extraction(
        fixture_graph, _client(tmp_path, openrouter), "m", None, None, workers=1
    )
    assert (report.retried, report.truncated, report.invalid_json) == (1, 1, 1)
