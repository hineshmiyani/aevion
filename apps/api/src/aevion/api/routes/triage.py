"""POST /api/triage: a triage dry run, or apply on the sandbox (SPEC section 8, ADR-0005)."""

from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aevion.api.deps import get_db
from aevion.api.routes.ask import _settings, get_llm
from aevion.api.routes.webhooks import BRAIN_ORG, SANDBOX_ORG, get_writer
from aevion.graph.client import GraphNotFoundError, OrgGraph
from aevion.graph.naming import graph_name_for
from aevion.graph.schema import bootstrap
from aevion.llm.client import LLMClient
from aevion.sandbox.apply import triage_sandbox_issue
from aevion.sandbox.writer import SandboxWriter
from aevion.triage.service import (
    ApplyNotAllowedError,
    IssueNotFoundError,
    Mode,
    TriageResponse,
    check_mode,
    triage,
)

router = APIRouter(prefix="/api", tags=["triage"])


class TriageRequest(BaseModel):
    org: str = Field(min_length=1, max_length=39)
    issue_key: str = Field(
        pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#[0-9]+$",
        description="e.g. 'FalkorDB/FalkorDB#3357'",
    )
    mode: Mode = "dry_run"


@router.post("/triage", response_model=TriageResponse)
def triage_route(
    body: TriageRequest,
    db: Annotated[Any, Depends(get_db)],
    llm: Annotated[LLMClient, Depends(get_llm)],
    writer: Annotated[SandboxWriter | None, Depends(get_writer)],
) -> TriageResponse:
    settings = _settings()
    try:
        check_mode(body.issue_key, body.mode, settings.triage_apply_repos)
    except ApplyNotAllowedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    try:
        graph = OrgGraph(db, graph_name_for(body.org))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if body.mode == "apply":
        return _apply(db, body.issue_key, llm, writer)
    try:
        return triage(
            graph,
            body.issue_key,
            body.mode,
            allowed_repos=settings.triage_apply_repos,
            client=llm,
            model=settings.agent_model,
        )
    except GraphNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"No graph for org {body.org!r}") from exc
    except IssueNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail=f"No issue {body.issue_key} in the graph"
        ) from exc


def _apply(db: Any, issue_key: str, llm: LLMClient, writer: SandboxWriter | None) -> TriageResponse:
    """Apply on a sandbox issue (already allow-listed by check_mode). Reads the issue from
    GitHub, so it works before any webhook has delivered it; a second apply returns the
    first run instead of commenting again."""
    if writer is None:
        raise HTTPException(status_code=503, detail="SANDBOX_GITHUB_TOKEN isn't set")
    settings = _settings()
    number = int(issue_key.rsplit("#", 1)[1])
    try:
        issue = writer.issue(number)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=404, detail=f"No issue {issue_key} on GitHub") from exc
    sandbox = OrgGraph(db, graph_name_for(SANDBOX_ORG))
    bootstrap(sandbox)
    repository = {
        "full_name": writer.repo,
        "html_url": f"https://github.com/{writer.repo}",
    }
    try:
        return triage_sandbox_issue(
            OrgGraph(db, graph_name_for(BRAIN_ORG)),
            sandbox,
            writer,
            repository,
            issue,
            client=llm,
            model=settings.agent_model,
            default_repo=settings.sandbox_default_repo,
        )
    except GraphNotFoundError as exc:
        raise HTTPException(status_code=404, detail="The FalkorDB graph isn't loaded") from exc
