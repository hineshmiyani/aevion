"""The fixed Cypher tools (ADR-0007), registered once and shared by the HTTP API, the
agent and the MCP server, so all three expose exactly the same tools and schemas.
"""

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from aevion.graph.client import OrgGraph
from aevion.tools.evidence import ToolResult
from aevion.tools.experts import ExpertsForArgs, experts_for


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    args_model: type[BaseModel]
    run: Callable[[OrgGraph, BaseModel], ToolResult]


def _tool(
    name: str,
    description: str,
    args_model: type[BaseModel],
    run: Callable[[OrgGraph, BaseModel], ToolResult],
) -> Tool:
    return Tool(name, description, args_model, run)


TOOLS: dict[str, Tool] = {
    tool.name: tool
    for tool in (
        _tool(
            "experts_for",
            "Who knows a Component? Ranks people by weighted, recent merged-PR authorship, "
            "reviews and comments in that part of the codebase, with the PRs as evidence.",
            ExpertsForArgs,
            experts_for,  # type: ignore[arg-type]
        ),
    )
}
