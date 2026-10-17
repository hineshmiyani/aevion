"""The MCP server publishes the registry tools and runs them on the org graph."""

import asyncio
import json
from typing import Any

import pytest

from aevion.graph.client import OrgGraph
from aevion.mcp.server import build_server
from aevion.tools.registry import TOOLS

pytestmark = pytest.mark.integration


def test_lists_every_registry_tool_with_flat_parameters(fixture_graph: OrgGraph) -> None:
    tools = asyncio.run(build_server(fixture_graph, "FalkorDB").list_tools())
    assert [t.name for t in tools] == list(TOOLS)
    experts = next(t for t in tools if t.name == "experts_for")
    assert {"component", "repo", "limit"} <= set(experts.input_schema["properties"])
    assert experts.input_schema.get("required") == ["component"]


def test_calls_a_tool_and_returns_rows_with_evidence(fixture_graph: OrgGraph) -> None:
    server = build_server(fixture_graph, "FalkorDB")
    result = asyncio.run(
        server.call_tool("experts_for", {"component": "falkordb", "repo": "FalkorDB/falkordb-py"})
    )
    payload: dict[str, Any] = result.structured_content or json.loads(result.content[0].text)  # type: ignore[union-attr]
    if "result" in payload and "rows" not in payload:
        payload = payload["result"]
    assert [row["login"] for row in payload["rows"]][:2] == ["alice", "bob"]
    assert payload["evidence"]["edges"] and payload["cypher"]
