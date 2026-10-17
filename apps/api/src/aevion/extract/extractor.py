"""LLM decision extraction (ADR-0011 §4). The model only proposes; everything it returns is
validated against the thread before it reaches the graph:

- people must have taken part in the thread,
- evidence comment ids must be real comments of the thread,
- Components must be ones the thread's PRs touched,
- low-confidence decisions (< 0.5) are dropped.
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from aevion.extract.candidates import Thread
from aevion.llm.client import ChatResult, LLMClient

MIN_CONFIDENCE = 0.5
MAX_DECISIONS_PER_THREAD = 2

SYSTEM_PROMPT = """You read one GitHub pull request or issue thread from an open-source project
and record the engineering DECISIONS it contains.

A decision is a deliberate choice about how the software or project works, with a reason:
"use a merge queue so forks can't edit the CI that judges them", "store timestamps as epoch
milliseconds", "drop Python 3.8 support". Routine bug fixes, typo fixes, version bumps and
"LGTM" are NOT decisions. Most threads contain no decision; returning none is expected.

Return JSON only, in exactly this shape:
{"decisions": [{
  "summary": "one sentence, present tense, what was decided",
  "rationale": "why, in the thread's own terms",
  "alternatives": ["options considered and rejected, if any"],
  "made_by": ["github logins who made or approved it"],
  "components": ["component keys from the list given, that it affects"],
  "evidence": ["comment ids like rc:123 that show it"],
  "confidence": 0.0
}]}

At most two decisions. Use only logins, component keys and comment ids that appear in the
thread. confidence is how sure you are this is a real, deliberate decision (0 to 1)."""


class _RawDecision(BaseModel):
    summary: str = Field(min_length=8, max_length=300)
    rationale: str = Field(default="", max_length=600)
    alternatives: list[str] = Field(default_factory=list)
    made_by: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class _RawResponse(BaseModel):
    decisions: list[_RawDecision] = Field(default_factory=list)


@dataclass(frozen=True)
class DecisionRec:
    id: str
    thread_key: str
    thread_label: str
    summary: str
    rationale: str
    alternatives: tuple[str, ...]
    decided_at: int | None
    confidence: float
    model: str
    source_url: str
    made_by: tuple[str, ...] = ()
    components: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()


@dataclass
class ExtractionResult:
    decisions: list[DecisionRec] = field(default_factory=list)
    dropped: int = 0
    invalid_json: bool = False


def extract_decisions(client: LLMClient, model: str, thread: Thread) -> ExtractionResult:
    result = client.chat(
        model,
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": thread.as_prompt_text()},
        ],
        max_tokens=700,
        response_format={"type": "json_object"},
        purpose="extract",
    )
    return parse_decisions(result, thread)


def parse_decisions(result: ChatResult, thread: Thread) -> ExtractionResult:
    out = ExtractionResult()
    try:
        raw = _RawResponse.model_validate(json.loads(_json_object(result.content)))
    except (json.JSONDecodeError, ValidationError, ValueError):
        out.invalid_json = True
        return out

    comment_ids = {c["id"] for c in thread.comments}
    for item in raw.decisions[:MAX_DECISIONS_PER_THREAD]:
        if item.confidence < MIN_CONFIDENCE:
            out.dropped += 1
            continue
        summary = " ".join(item.summary.split())
        digest = hashlib.sha256(f"{thread.key}|{summary.lower()}".encode()).hexdigest()[:16]
        out.decisions.append(
            DecisionRec(
                id=f"dec:{digest}",
                thread_key=thread.key,
                thread_label=thread.label,
                summary=summary,
                rationale=item.rationale.strip(),
                alternatives=tuple(a.strip() for a in item.alternatives if a.strip())[:4],
                decided_at=thread.decided_at,
                confidence=round(item.confidence, 2),
                model=result.model,
                source_url=thread.url,
                made_by=tuple(p for p in dict.fromkeys(item.made_by) if p in thread.participants),
                components=tuple(
                    c for c in dict.fromkeys(item.components) if c in thread.components
                ),
                evidence=tuple(e for e in dict.fromkeys(item.evidence) if e in comment_ids),
            )
        )
    return out


def _json_object(text: str) -> str:
    """Some models wrap JSON in prose or a code fence; take the outermost object."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in response")
    return text[start : end + 1]


def estimate_tokens(thread: Thread) -> int:
    """~4 characters per token for English text, plus the fixed system prompt."""
    return (len(SYSTEM_PROMPT) + len(thread.as_prompt_text())) // 4


def as_rows(decisions: list[DecisionRec]) -> list[dict[str, Any]]:
    from dataclasses import asdict

    return [asdict(d) for d in decisions]
