"""The agent loop (SPEC module `agent`): question → tool calls → cited answer.

The model picks tools; the tools do the graph work. Each tool result is handed back as
compact rows plus globally numbered sources. The model cites sources as [n]; afterwards the
citations are renumbered in reading order and mapped to evidence node ids, so the UI can
light each one on the evidence trail.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from aevion.agent.prompts import NO_TOOLS_LEFT, NOTHING_FOUND, SYSTEM_PROMPT
from aevion.graph.client import OrgGraph
from aevion.llm.client import LLMClient
from aevion.tools.evidence import EvidenceBuilder, EvidencePath, ToolResult
from aevion.tools.registry import TOOLS

MAX_TOOL_CALLS = 4
MAX_RESULT_CHARS = 6000  # per tool result handed to the model
_CITATION = re.compile(r"\[(\d+)\]")


class Citation(BaseModel):
    n: int
    node_id: str


class ToolCallRecord(BaseModel):
    tool: str
    args: dict[str, Any]


class AskResponse(BaseModel):
    """The /api/ask contract (SPEC section 8)."""

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    evidence: EvidencePath = Field(default_factory=EvidencePath)
    cypher: list[str] = Field(default_factory=list)
    model: str
    cached: bool


def tool_specs() -> list[dict[str, Any]]:
    """OpenAI-style function specs, generated from the same registry the API and MCP use."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.args_model.model_json_schema(),
            },
        }
        for tool in TOOLS.values()
    ]


@dataclass
class _Sources:
    """Numbers evidence nodes across all tool calls so the model can cite them."""

    numbers: dict[str, int] = field(default_factory=dict)

    def number(self, node_id: str) -> int:
        return self.numbers.setdefault(node_id, len(self.numbers) + 1)

    def node_for(self, n: int) -> str | None:
        return next((node for node, k in self.numbers.items() if k == n), None)


def ask(graph: OrgGraph, client: LLMClient, model: str, org: str, question: str) -> AskResponse:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT.format(org=org, max_calls=MAX_TOOL_CALLS)},
        {"role": "user", "content": question},
    ]
    specs = tool_specs()
    sources = _Sources()
    evidence = _MergedEvidence()
    calls: list[ToolCallRecord] = []
    cypher: list[str] = []
    all_cached = True
    answer = ""

    while True:
        out_of_calls = len(calls) >= MAX_TOOL_CALLS
        if out_of_calls:
            messages.append({"role": "user", "content": NO_TOOLS_LEFT})
        result = client.chat(
            model, messages, tools=None if out_of_calls else specs, purpose="agent"
        )
        all_cached = all_cached and result.cached
        if not result.tool_calls or out_of_calls:
            answer = result.content.strip()
            break

        messages.append(
            {
                "role": "assistant",
                "content": result.content or None,
                "tool_calls": result.tool_calls,
            }
        )
        for raw_call, (name, arguments) in zip(
            result.tool_calls, result.tool_arguments(), strict=True
        ):
            if len(calls) >= MAX_TOOL_CALLS:
                content = "Not run: the tool-call limit was reached."
            else:
                calls.append(ToolCallRecord(tool=name, args=arguments))
                content = _run_tool(graph, name, arguments, sources, evidence, cypher)
            messages.append(
                {"role": "tool", "tool_call_id": raw_call.get("id", name), "content": content}
            )

    if not answer or (not evidence.has_content() and not calls):
        answer = answer or NOTHING_FOUND
    text, citations = _renumber(answer, sources)
    return AskResponse(
        answer=text,
        citations=citations,
        tool_calls=calls,
        evidence=evidence.build(),
        cypher=cypher,
        model=model,
        cached=all_cached,
    )


def _run_tool(
    graph: OrgGraph,
    name: str,
    arguments: dict[str, Any],
    sources: _Sources,
    evidence: "_MergedEvidence",
    cypher: list[str],
) -> str:
    tool = TOOLS.get(name)
    if tool is None:
        return f"Error: there is no tool called {name!r}. Available: {', '.join(TOOLS)}."
    try:
        args = tool.args_model.model_validate(arguments)
    except ValidationError as exc:
        return f"Error: invalid arguments for {name}: {exc.errors()[0]['msg']}. Fix them and retry."
    result: ToolResult = tool.run(graph, args)
    evidence.add(result.evidence)
    cypher.extend(q for q in result.cypher if q not in cypher)
    if not result.rows:
        return f"{name} found nothing for {json.dumps(arguments)}."
    numbered = [f"[{sources.number(n.id)}] {n.label}: {n.title}" for n in result.evidence.nodes]
    payload = json.dumps(result.rows, default=str)
    if len(payload) > MAX_RESULT_CHARS:
        payload = payload[:MAX_RESULT_CHARS] + " …(truncated)"
    return f"Result rows:\n{payload}\n\nSources (cite by number):\n" + "\n".join(numbered)


def _renumber(answer: str, sources: _Sources) -> tuple[str, list[Citation]]:
    """Renumber [n] markers in reading order; drop markers that don't name a real source."""
    mapping: dict[int, int] = {}
    citations: list[Citation] = []

    def replace(match: re.Match[str]) -> str:
        original = int(match.group(1))
        node_id = sources.node_for(original)
        if node_id is None:
            return ""
        if original not in mapping:
            mapping[original] = len(mapping) + 1
            citations.append(Citation(n=mapping[original], node_id=node_id))
        return f"[{mapping[original]}]"

    text = _CITATION.sub(replace, answer)
    return re.sub(r"[ \t]+([.,;:])", r"\1", text).strip(), citations


class _MergedEvidence:
    """One evidence path across every tool call, nodes and edges deduplicated."""

    def __init__(self) -> None:
        self._builder = EvidenceBuilder()

    def add(self, path: EvidencePath) -> None:
        for node in path.nodes:
            label, key = node.id.split(":", 1)
            self._builder.node(label, key, title=node.title, url=node.url)
        for edge in path.edges:
            self._builder.edge(edge.source, edge.type, edge.target)

    def has_content(self) -> bool:
        return bool(self._builder.build().nodes)

    def build(self) -> EvidencePath:
        return self._builder.build()
