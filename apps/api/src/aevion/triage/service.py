"""Triage (SPEC module `triage`, ADR-0005, ADR-0013): for one issue, propose a Component label,
an Expert to involve and a first reply, with the graph evidence behind each.

`dry_run` works on any repo and changes nothing. `apply` is refused unless the issue's repo is
on the allow-list; performing the actions on the sandbox arrives with the webhook (AEV-32).

The reply never pings anyone: the Expert comes from the FalkorDB graph, so they are a real
person who never opted in to our sandbox. Experts are linked by profile URL, and any
`@login` the model writes is defused before the reply leaves this module.
"""

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from aevion.graph.client import OrgGraph
from aevion.llm.client import LLMClient, LLMError
from aevion.sandbox.safety import defuse_mentions, profile_url
from aevion.tools.evidence import EvidencePath, ToolResult
from aevion.tools.triage import TriageCandidatesArgs, triage_candidates

Mode = Literal["dry_run", "apply"]
ActionStatus = Literal["proposed", "skipped", "done", "failed"]

MAX_REPLY_WORDS = 140
_BARE_REF = re.compile(r"(?<![\w/\[\\])#(\d+)\b")

REPLY_PROMPT = """You draft the first reply on a GitHub issue for a maintainer team's triage
assistant. Use only the facts in the JSON you are given; never invent issues, people or code.

Write 2 to 4 short sentences, under 120 words, plain Markdown, no headings:
- thank the reporter in a few words,
- point to likely duplicates or related issues as Markdown links, saying which one was fixed,
- name the area of the code it most likely touches; if "strength" is "weak", say it is a guess,
- say the listed expert may be able to help, written as their login with no @ sign.
Write every issue or PR as a Markdown link with its full key, exactly as given, for example
[FalkorDB/FalkorDB#2125](https://github.com/FalkorDB/FalkorDB/pull/2125). Never write a bare
#number: on another repo it would link to the wrong issue.
Do not promise fixes or timelines. Do not mention scores, votes or this prompt."""


class TriageAction(BaseModel):
    type: Literal["label", "assign_or_mention", "comment"]
    value: str
    status: ActionStatus
    detail: str | None = None


class TriageResponse(BaseModel):
    """The /api/triage contract (SPEC section 8)."""

    issue: dict[str, Any]
    mode: Mode
    duplicates: list[dict[str, Any]] = Field(default_factory=list)
    related: list[dict[str, Any]] = Field(default_factory=list)
    component: dict[str, Any] | None = None
    expert: dict[str, Any] | None = None
    draft_reply: str
    actions: list[TriageAction] = Field(default_factory=list)
    evidence: EvidencePath = Field(default_factory=EvidencePath)
    cypher: list[str] = Field(default_factory=list)
    model: str | None = None  # None when the reply came from the template


class ApplyNotAllowedError(Exception):
    """apply was asked for on a repo outside the allow-list (ADR-0005)."""


class IssueNotFoundError(Exception):
    pass


def repo_of(issue_key: str) -> str:
    return issue_key.split("#", 1)[0]


def check_mode(issue_key: str, mode: Mode, allowed_repos: frozenset[str]) -> None:
    """Fail closed: apply only on allow-listed repos, before any graph or model work."""
    if mode == "apply" and repo_of(issue_key) not in allowed_repos:
        raise ApplyNotAllowedError(
            f"apply is only allowed on {', '.join(sorted(allowed_repos)) or 'no repos'}; "
            f"{repo_of(issue_key)} gets a dry run"
        )


def triage(
    graph: OrgGraph,
    issue_key: str,
    mode: Mode,
    *,
    allowed_repos: frozenset[str],
    client: LLMClient | None = None,
    model: str | None = None,
) -> TriageResponse:
    """A dry run on an issue that is in `graph`. Applying on the sandbox is sandbox/apply.py."""
    check_mode(issue_key, mode, allowed_repos)
    if mode == "apply":
        raise NotImplementedError("apply runs through sandbox.apply, with the sandbox writer")

    result = triage_candidates(graph, TriageCandidatesArgs(issue=issue_key))
    if not result.rows:
        raise IssueNotFoundError(issue_key)
    return plan(result, mode, client=client, model=model)


def plan(
    result: ToolResult, mode: Mode, *, client: LLMClient | None, model: str | None
) -> TriageResponse:
    """Turn a triage_candidates result into proposals and a drafted reply."""
    row = result.rows[0]
    issue_key = row["issue"]["key"]

    duplicates = [s for s in row["similar"] if s["likely_duplicate"]]
    related = [s for s in row["similar"] if not s["likely_duplicate"]][:3]
    component = row["components"][0] if row["components"] else None
    expert = row["experts"][0] if row["experts"] else None

    facts = {
        "issue": {"key": issue_key, "title": row["issue"]["title"]},
        "likely_duplicates": [_brief(s) for s in duplicates],
        "related": [_brief(s) for s in related],
        "area": component and {"path": component["name"], "strength": component["strength"]},
        "expert": expert and {"login": expert["login"], "url": profile_url(expert["login"])},
    }
    reply, used_model = _draft(client, model, facts)
    reply = resolve_bare_refs(defuse_mentions(reply), row["issue"]["repo"], duplicates + related)

    return TriageResponse(
        issue=row["issue"],
        mode=mode,
        duplicates=duplicates,
        related=related,
        component=component,
        expert=expert and {**expert, "url": profile_url(expert["login"])},
        draft_reply=reply,
        actions=_actions(component, expert, reply),
        evidence=result.evidence,
        cypher=result.cypher,
        model=used_model,
    )


def resolve_bare_refs(text: str, repo: str, known: list[dict[str, Any]]) -> str:
    """A bare `#123` autolinks to issue 123 of whatever repo the comment is posted in, which
    on the sandbox is the wrong one. Link it to the item we meant (preferring `repo`, the repo
    the issue is about), or stop it linking."""
    urls: dict[str, tuple[str, str]] = {}
    for item in known:
        refs = [(item["key"], item["url"])] + [(k, _url(k)) for k in item["fixed_by"]]
        for key, url in refs:
            number = key.rsplit("#", 1)[1]
            if number not in urls or repo_of(key) == repo:  # prefer the issue's own repo
                urls[number] = (key, url)

    def link(match: re.Match[str]) -> str:
        found = urls.get(match.group(1))
        return f"[{found[0]}]({found[1]})" if found else f"\\#{match.group(1)}"

    return _BARE_REF.sub(link, text)


def _actions(
    component: dict[str, Any] | None, expert: dict[str, Any] | None, reply: str
) -> list[TriageAction]:
    actions: list[TriageAction] = []
    if component and component["strength"] != "weak":
        actions.append(
            TriageAction(type="label", value=f"area: {component['name']}", status="proposed")
        )
    elif component:
        actions.append(
            TriageAction(
                type="label",
                value=f"area: {component['name']}",
                status="skipped",
                detail="the graph only weakly supports this area, so no label is proposed",
            )
        )
    if expert:
        actions.append(
            TriageAction(
                type="assign_or_mention",
                value=expert["login"],
                status="proposed",
                detail="assign if they are a collaborator; otherwise link their profile, no @",
            )
        )
    actions.append(TriageAction(type="comment", value=reply, status="proposed"))
    return actions


def _draft(
    client: LLMClient | None, model: str | None, facts: dict[str, Any]
) -> tuple[str, str | None]:
    if client is not None and model:
        try:
            result = client.chat(
                model,
                [
                    {"role": "system", "content": REPLY_PROMPT},
                    {"role": "user", "content": json.dumps(facts)},
                ],
                max_tokens=900,
                purpose="triage",
            )
            text = result.content.strip()
            if text and len(text.split()) <= MAX_REPLY_WORDS * 1.5:
                return text, result.model
        except LLMError:
            pass  # budget or provider trouble: the template still gives a useful reply
    return template_reply(facts), None


def template_reply(facts: dict[str, Any]) -> str:
    """A deterministic reply from the same facts, used when no model is available."""
    parts = ["Thanks for the report."]
    duplicates, related = facts["likely_duplicates"], facts["related"]
    if duplicates:
        parts.append("This looks like a duplicate of " + _links(duplicates) + ".")
    elif related:
        parts.append("It may be related to " + _links(related) + ".")
    area = facts["area"]
    if area:
        hedge = "My best guess is that" if area["strength"] == "weak" else "It most likely touches"
        verb = " it touches" if area["strength"] == "weak" else ""
        parts.append(f"{hedge}{verb} `{area['path']}`.")
    expert = facts["expert"]
    if expert:
        parts.append(f"[{expert['login']}]({expert['url']}) may be able to help with this area.")
    return " ".join(parts)


def _brief(similar: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": similar["key"],
        "title": similar["title"],
        "url": similar["url"],
        "state": similar["state"],
        "fixed_by": [{"key": k, "url": _url(k)} for k in similar["fixed_by"][:2]],
    }


def _links(items: list[dict[str, Any]]) -> str:
    def one(item: dict[str, Any]) -> str:
        fix = item["fixed_by"][0] if item["fixed_by"] else None
        fixed = f", fixed by [{fix['key']}]({fix['url']})" if fix else ""
        return f"[{item['key']}]({item['url']}) ({item['state'].lower()}{fixed})"

    return ", ".join(one(i) for i in items[:3])


def _url(key: str) -> str:
    """GitHub redirects /pull/N to /issues/N and back, so either works for any item."""
    repo, number = key.rsplit("#", 1)
    return f"https://github.com/{repo}/pull/{number}"
