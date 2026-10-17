"""POST /api/ask: the agent over HTTP (SPEC section 8)."""

from functools import lru_cache
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aevion.agent.loop import AskResponse, ask
from aevion.api.deps import get_db
from aevion.config import Settings
from aevion.graph.client import GraphNotFoundError, OrgGraph
from aevion.graph.naming import graph_name_for
from aevion.llm.client import BudgetExceededError, LLMClient, LLMError
from aevion.llm.factory import llm_client

router = APIRouter(prefix="/api", tags=["ask"])


class AskRequest(BaseModel):
    org: str = Field(min_length=1, max_length=39)
    question: str = Field(min_length=1, max_length=500)


@lru_cache(maxsize=1)
def _settings() -> Settings:
    return Settings()


def get_llm() -> LLMClient:
    return llm_client(_settings())


@router.post("/ask", response_model=AskResponse)
def ask_route(
    body: AskRequest,
    db: Annotated[Any, Depends(get_db)],
    llm: Annotated[LLMClient, Depends(get_llm)],
) -> AskResponse:
    try:
        graph = OrgGraph(db, graph_name_for(body.org))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        return ask(graph, llm, _settings().agent_model, body.org, body.question.strip())
    except GraphNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"No graph for org {body.org!r}") from exc
    except BudgetExceededError as exc:
        raise HTTPException(
            status_code=503, detail="Aevion's question budget is used up for now."
        ) from exc
    except LLMError as exc:
        raise HTTPException(
            status_code=503, detail="The language model is unavailable. Try again shortly."
        ) from exc
