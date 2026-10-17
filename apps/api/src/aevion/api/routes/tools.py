"""POST /api/tools/{tool}: call one fixed Cypher tool directly (SPEC section 8)."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import ValidationError

from aevion.api.deps import get_db
from aevion.graph.client import GraphNotFoundError, OrgGraph
from aevion.graph.naming import graph_name_for
from aevion.tools.evidence import ToolResult
from aevion.tools.registry import TOOLS

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("")
def list_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "parameters": t.args_model.model_json_schema(),
        }
        for t in TOOLS.values()
    ]


@router.post("/{tool_name}", response_model=ToolResult)
def call_tool(
    tool_name: str,
    db: Annotated[Any, Depends(get_db)],
    payload: Annotated[dict[str, Any], Body()],
) -> ToolResult:
    tool = TOOLS.get(tool_name)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Unknown tool {tool_name!r}")
    org = payload.pop("org", None)
    if not org:
        raise HTTPException(status_code=422, detail="'org' is required")
    try:
        graph_name = graph_name_for(org)
        args = tool.args_model.model_validate(payload)
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        return tool.run(OrgGraph(db, graph_name), args)
    except GraphNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"No graph for org {org!r}") from exc
