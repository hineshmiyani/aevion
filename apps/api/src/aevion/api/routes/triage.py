"""POST /api/triage: a triage dry run, or apply on the sandbox (SPEC section 8, ADR-0005)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aevion.api.deps import get_db
from aevion.api.routes.ask import _settings, get_llm
from aevion.graph.client import GraphNotFoundError, OrgGraph
from aevion.graph.naming import graph_name_for
from aevion.llm.client import LLMClient
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
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
