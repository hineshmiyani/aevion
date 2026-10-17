"""MCP server exposing Aevion's graph tools (SPEC module `mcp`, US-7).

Every tool in the registry is published with the same name, description and parameters as
`/api/tools`, so Claude Code, Cursor or any MCP client queries the company brain directly.
Uses the MCP Python SDK v2 (`MCPServer`, formerly `FastMCP`).
"""

import inspect
from collections.abc import Callable
from typing import Any

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel

from aevion.graph.client import OrgGraph
from aevion.tools.registry import TOOLS, Tool

INSTRUCTIONS = (
    "Aevion is a company brain for the {org} GitHub organisation, stored in FalkorDB. Use "
    "experts_for to find who knows a part of the code, decision_trail for why something was "
    "decided, area_history for what's happening in a directory, related_work for what an issue "
    "or PR touches, and catch_up for what changed since a date. Every result includes an "
    "evidence path: the graph nodes and edges behind the answer, with GitHub links."
)


def _wrapper(tool: Tool, graph: OrgGraph) -> Callable[..., dict[str, Any]]:
    """A function whose signature is the tool's argument model, so MCP sees flat parameters."""

    def call(**kwargs: Any) -> dict[str, Any]:
        args: BaseModel = tool.args_model.model_validate(kwargs)
        result = tool.run(graph, args)
        return {
            "rows": result.rows,
            "evidence": result.evidence.model_dump(),
            "cypher": result.cypher,
        }

    params = [
        inspect.Parameter(
            name,
            inspect.Parameter.KEYWORD_ONLY,
            default=inspect.Parameter.empty if field.is_required() else field.default,
            annotation=field.annotation,
        )
        for name, field in tool.args_model.model_fields.items()
    ]
    call.__signature__ = inspect.Signature(params, return_annotation=dict[str, Any])  # type: ignore[attr-defined]
    call.__annotations__ = {p.name: p.annotation for p in params} | {"return": dict[str, Any]}
    call.__name__ = tool.name
    call.__doc__ = tool.description
    return call


def build_server(graph: OrgGraph, org: str) -> MCPServer:
    server: MCPServer = MCPServer(
        name="aevion",
        title=f"Aevion: {org} company brain",
        instructions=INSTRUCTIONS.format(org=org),
        version="0.1.0",
    )
    for tool in TOOLS.values():
        server.add_tool(_wrapper(tool, graph), name=tool.name, description=tool.description)
    return server
