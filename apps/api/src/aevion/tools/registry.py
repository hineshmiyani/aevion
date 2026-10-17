"""The fixed Cypher tools (ADR-0007), registered once and shared by the HTTP API, the
agent and the MCP server, so all three expose exactly the same tools and schemas.
"""

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from aevion.graph.client import OrgGraph
from aevion.tools.catch_up import CatchUpArgs, catch_up
from aevion.tools.decisions import DecisionTrailArgs, decision_trail
from aevion.tools.evidence import ToolResult
from aevion.tools.experts import ExpertsForArgs, experts_for
from aevion.tools.history import AreaHistoryArgs, area_history
from aevion.tools.related import RelatedWorkArgs, related_work


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
        _tool(
            "decision_trail",
            "Why was something decided? Finds Decisions extracted from PR and issue threads, with "
            "the thread, the comments that show it, who made it, and what it replaced.",
            DecisionTrailArgs,
            decision_trail,  # type: ignore[arg-type]
        ),
        _tool(
            "area_history",
            "What's the history of a Component? Recent merged PRs, open issues tied to that code, "
            "and the people most active there.",
            AreaHistoryArgs,
            area_history,  # type: ignore[arg-type]
        ),
        _tool(
            "related_work",
            "What else does an issue or PR touch? Linked issues and PRs, the files and Components "
            "involved, and other PRs changing the same files.",
            RelatedWorkArgs,
            related_work,  # type: ignore[arg-type]
        ),
        _tool(
            "catch_up",
            "Catch me up on a Component or repo since a date: merged PRs, issues they closed, "
            "releases, and who drove the work.",
            CatchUpArgs,
            catch_up,  # type: ignore[arg-type]
        ),
    )
}
