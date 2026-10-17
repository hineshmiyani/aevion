"""POST /webhooks/github: sandbox issue events in, triage out (SPEC `sync`, AEV-32).

GitHub signs each delivery with the shared secret; unsigned or wrongly signed requests are
refused before the body is even parsed. Only the sandbox repo's events are handled. A new
issue is triaged in the background so GitHub gets its 202 at once; edits, closes and comments
are just ingested, so our own triage comment can never trigger another triage.
"""

import hashlib
import hmac
import json
import logging
from functools import lru_cache
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request

from aevion.api.deps import get_db
from aevion.api.routes.ask import _settings, get_llm
from aevion.graph.client import OrgGraph
from aevion.graph.naming import graph_name_for
from aevion.graph.schema import bootstrap
from aevion.ingest.org_config import load_org_config
from aevion.llm.client import LLMClient
from aevion.sandbox.apply import ingest_issue, triage_sandbox_issue
from aevion.sandbox.writer import SandboxWriter, WriteNotAllowedError

router = APIRouter(tags=["webhooks"])
log = logging.getLogger("aevion.webhooks")

BRAIN_ORG = "FalkorDB"
SANDBOX_ORG = "aevion-sandbox"


@lru_cache(maxsize=1)
def repo_hints() -> dict[str, tuple[str, ...]]:
    return load_org_config(_settings().org_config_path).triage_hints()


def get_writer() -> SandboxWriter | None:
    settings = _settings()
    try:
        return SandboxWriter(
            settings.sandbox_github_token or "", settings.sandbox_repo, settings.triage_apply_repos
        )
    except WriteNotAllowedError:
        return None


def signature_ok(secret: str, body: bytes, header: str | None) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return header is not None and hmac.compare_digest(expected, header)


@router.post("/webhooks/github", status_code=202)
async def github_webhook(
    request: Request,
    background: BackgroundTasks,
    db: Annotated[Any, Depends(get_db)],
    llm: Annotated[LLMClient, Depends(get_llm)],
    writer: Annotated[SandboxWriter | None, Depends(get_writer)],
    x_github_event: Annotated[str | None, Header()] = None,
    x_hub_signature_256: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    settings = _settings()
    if not settings.github_webhook_secret:
        raise HTTPException(status_code=503, detail="The webhook isn't configured")
    body = await request.body()
    if not signature_ok(settings.github_webhook_secret, body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Bad signature")

    payload = json.loads(body)
    if x_github_event == "ping":
        return {"status": "pong"}
    repository = payload.get("repository") or {}
    if repository.get("full_name") not in settings.triage_apply_repos:
        return {"status": "ignored: not the sandbox"}
    issue = payload.get("issue")
    if x_github_event not in ("issues", "issue_comment") or not issue or "pull_request" in issue:
        return {"status": "ignored: not an issue event"}

    sandbox = OrgGraph(db, graph_name_for(SANDBOX_ORG))
    bootstrap(sandbox)
    if x_github_event == "issues" and payload.get("action") == "opened":
        if writer is None:
            raise HTTPException(status_code=503, detail="SANDBOX_GITHUB_TOKEN isn't set")
        background.add_task(
            _triage,
            OrgGraph(db, graph_name_for(BRAIN_ORG)),
            sandbox,
            writer,
            repository,
            issue,
            llm,
        )
        return {"status": "accepted: triaging"}
    comment = payload.get("comment") if x_github_event == "issue_comment" else None
    ingest_issue(sandbox, repository, issue, [comment] if comment else None)
    return {"status": "accepted: ingested"}


def _triage(
    brain: OrgGraph,
    sandbox: OrgGraph,
    writer: SandboxWriter,
    repository: dict[str, Any],
    issue: dict[str, Any],
    llm: LLMClient,
) -> None:
    settings = _settings()
    try:
        response = triage_sandbox_issue(
            brain,
            sandbox,
            writer,
            repository,
            issue,
            client=llm,
            model=settings.agent_model,
            default_repo=settings.sandbox_default_repo,
            repo_hints=repo_hints(),
        )
        log.info("triaged %s: %s", response.issue["key"], [a.status for a in response.actions])
    except Exception:  # a background task has no caller to report to; log it and move on
        log.exception("triage failed for %s#%s", repository.get("full_name"), issue.get("number"))
