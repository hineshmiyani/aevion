"""Triage a sandbox issue for real: ingest it, plan with the FalkorDB graph, act, record.

Two graphs are involved. The sandbox issue goes into `org:aevion-sandbox`, with a TriageRun
node recording what was done. The reasoning (similar issues, Components, Experts) runs on the
FalkorDB graph, because that is where the knowledge is. A seeded copy is triaged in its
original's repo; an issue someone types fresh is triaged against FalkorDB core by default.

Every write goes through SandboxWriter, and everything posted passes safe_for_sandbox.
"""

import json
import time
from typing import Any

import httpx

from aevion.graph.client import OrgGraph
from aevion.ingest.loader import load_batch, upsert_repo
from aevion.ingest.normalize import Batch, issue_from
from aevion.llm.client import LLMClient
from aevion.sandbox.safety import profile_url, safe_for_sandbox
from aevion.sandbox.seed import original_of
from aevion.sandbox.writer import SandboxWriter
from aevion.tools.triage import infer_repo, triage_issue
from aevion.triage.service import TriageAction, TriageResponse, plan

LABEL_COLOR = "8a560f"  # Aevion's evidence-path amber
MAX_LABEL = 50  # GitHub's limit on label names

RECORD_RUN = """
MATCH (i:Issue {key: $key})
MERGE (t:TriageRun {issue_key: $key})
SET t.at = $at, t.result = $result
MERGE (t)-[:FOR]->(i)
"""

LAST_RUN = """
MATCH (t:TriageRun {issue_key: $key})
RETURN t.result AS result
"""


def ingest_issue(
    graph: OrgGraph,
    repository: dict[str, Any],
    issue: dict[str, Any],
    comments: list[dict[str, Any]] | None = None,
) -> str:
    """A REST (webhook) issue → the same records ingestion builds from GraphQL, then MERGE."""
    repo = upsert_repo(
        graph, {"nameWithOwner": repository["full_name"], "url": repository["html_url"]}
    )
    batch = Batch()
    node = {
        "number": issue["number"],
        "title": issue.get("title") or "",
        "body": issue.get("body") or "",
        "state": (issue.get("state") or "open").upper(),
        "url": issue["html_url"],
        "createdAt": issue.get("created_at"),
        "closedAt": issue.get("closed_at"),
        "updatedAt": issue.get("updated_at"),
        "author": _actor(issue.get("user")),
        "assignees": {"nodes": [_actor(a) for a in issue.get("assignees") or []]},
        "comments": {
            "nodes": [
                {
                    "author": _actor(c.get("user")),
                    "body": c.get("body") or "",
                    "databaseId": c.get("id"),
                    "url": c.get("html_url"),
                    "createdAt": c.get("created_at"),
                }
                for c in comments or []
            ]
        },
        "labels": {
            "nodes": [
                {"name": lb["name"], "color": lb.get("color")} for lb in issue.get("labels") or []
            ]
        },
    }
    record = issue_from(node, repo, frozenset(), batch)
    load_batch(graph, batch)
    return record.key


def last_run(graph: OrgGraph, issue_key: str) -> TriageResponse | None:
    rows = graph.ro_query(LAST_RUN, {"key": issue_key}).rows
    return TriageResponse.model_validate_json(rows[0][0]) if rows and rows[0][0] else None


def triage_sandbox_issue(
    brain: OrgGraph,
    sandbox_graph: OrgGraph,
    writer: SandboxWriter,
    repository: dict[str, Any],
    issue: dict[str, Any],
    *,
    client: LLMClient | None,
    model: str | None,
    default_repo: str,
    repo_hints: dict[str, tuple[str, ...]] | None = None,
    force: bool = False,
) -> TriageResponse:
    key = ingest_issue(sandbox_graph, repository, issue)
    if not force and (previous := last_run(sandbox_graph, key)):
        return previous  # a redelivered webhook or a second click never comments twice

    original = original_of(issue)
    if original:
        repo, why = original.split("#", 1)[0], [f"a copy of `{original}`"]
    else:
        repo, why = infer_repo(
            brain, issue.get("title") or "", issue.get("body") or "", repo_hints or {}, default_repo
        )
    context = {
        "key": key,
        "title": issue.get("title") or "",
        "body": issue.get("body") or "",
        "state": (issue.get("state") or "open").upper(),
        "url": issue["html_url"],
        "repo": repo,
        "author": (issue.get("user") or {}).get("login"),
    }
    response = plan(triage_issue(brain, context), "apply", client=client, model=model)
    response.issue = {**response.issue, "key": key, "context_repo": repo, "context_reason": why}
    response.actions = apply_actions(writer, issue["number"], response)
    sandbox_graph.query(
        RECORD_RUN,
        {"key": key, "at": int(time.time() * 1000), "result": response.model_dump_json()},
    )
    return response


def apply_actions(
    writer: SandboxWriter, number: int, response: TriageResponse
) -> list[TriageAction]:
    done: list[TriageAction] = []
    for action in response.actions:
        try:
            done.append(_apply(writer, number, action, response))
        except httpx.HTTPError as exc:
            done.append(action.model_copy(update={"status": "failed", "detail": _reason(exc)}))
    return done


def comment_body(response: TriageResponse, sandbox_repo: str) -> str:
    footer_bits = []
    if response.component:
        footer_bits.append(
            f"area `{response.component['name']}` ({response.component['strength']})"
        )
    if response.expert:
        login = response.expert["login"]
        footer_bits.append(f"who knows it: [{login}]({profile_url(login)})")
    similar = [s["key"] for s in response.duplicates + response.related][:3]
    if similar:
        footer_bits.append("similar " + ", ".join(similar))
    footer = (
        "\n\n<sub>Suggested by Aevion's triage agent from the FalkorDB knowledge graph"
        + (": " + "; ".join(footer_bits) if footer_bits else "")
        + ". A maintainer should confirm.</sub>"
    )
    return safe_for_sandbox(response.draft_reply + footer, sandbox_repo)


def _apply(
    writer: SandboxWriter, number: int, action: TriageAction, response: TriageResponse
) -> TriageAction:
    if action.status == "skipped":
        return action
    if action.type == "label":
        label = action.value[:MAX_LABEL]
        writer.ensure_label(label, LABEL_COLOR, "Suggested by Aevion triage")
        writer.add_labels(number, [label])
        return action.model_copy(update={"status": "done", "value": label})
    if action.type == "assign_or_mention":
        if writer.is_collaborator(action.value):
            writer.assign(number, action.value)
            return action.model_copy(update={"status": "done", "detail": "assigned"})
        return action.model_copy(
            update={
                "status": "done",
                "detail": "not a collaborator here, so named in the comment by profile link (no @)",
            }
        )
    posted = writer.comment(number, comment_body(response, writer.repo))
    return action.model_copy(
        update={
            "status": "done",
            "value": posted.get("body", action.value),
            "detail": posted.get("html_url"),
        }
    )


def _actor(user: dict[str, Any] | None) -> dict[str, Any] | None:
    if not user:
        return None
    return {"__typename": "Bot" if user.get("type") == "Bot" else "User", "login": user["login"]}


def _reason(exc: httpx.HTTPError) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            message = json.loads(exc.response.text).get("message", "")
        except ValueError:
            message = ""
        return f"GitHub {exc.response.status_code}: {message}".strip()
    return f"GitHub unreachable: {type(exc).__name__}"
