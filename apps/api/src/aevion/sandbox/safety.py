"""Text we post on the sandbox must not reach anyone outside it (ADR-0005, ADR-0013).

Two GitHub behaviours would leak out of our public sandbox:

- `@login` notifies that person. Experts and copied-issue authors are real FalkorDB people.
- A reference to another repo's issue or PR (`FalkorDB/FalkorDB#123`, or its URL) adds a
  "mentioned this issue" event to that issue's timeline, a visible trace on a repo we don't own.
  GitHub creates neither from inside a code span, so foreign references become code spans.
"""

import re
from collections.abc import Callable

_MENTION = re.compile(r"(?<![\w/`])@([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))")
# The tail (#issuecomment-1, /files) never ends on punctuation: "…/issues/14." keeps its stop.
_ITEM_URL = (
    r"https?://(?:www\.)?github\.com/([\w.-]+/[\w.-]+)/(?:issues|pull)/(\d+)"
    r"(?:[/#?][^\s)\]]*[^\s)\].,;:!?])?"
)
# [text](github issue or PR url) — the whole link, so its text goes too.
_LINKED_ITEM = re.compile(r"\[([^\]]*)\]\(" + _ITEM_URL + r"\)")
_BARE_ITEM_URL = re.compile(r"(?<![(`<])" + _ITEM_URL)
_SHORTHAND = re.compile(r"(?<![\w/`.-])([\w.-]+/[\w.-]+)#(\d+)\b")
_CODE = re.compile(r"(```.*?```|`[^`\n]*`)", re.S)
_BARE_REF = re.compile(r"(?<![\w/\[`\\&])#(\d+)\b")


def profile_url(login: str) -> str:
    return f"https://github.com/{login}"


def defuse_mentions(text: str) -> str:
    """`@login` → `[login](profile)`: same person, same link, no notification. Code is left
    alone: GitHub doesn't notify from it, and rewriting it would corrupt it."""
    return _outside_code(
        text, lambda p: _MENTION.sub(lambda m: f"[{m.group(1)}]({profile_url(m.group(1))})", p)
    )


def inert_references(text: str, own_repo: str) -> str:
    """Turn references to other repos' issues and PRs into code spans; keep our own as links."""

    def outside_code(segment: str) -> str:
        def linked(m: re.Match[str]) -> str:
            repo, number = m.group(2), m.group(3)
            return m.group(0) if repo == own_repo else f"`{repo}#{number}`"

        def url(m: re.Match[str]) -> str:
            repo, number = m.group(1), m.group(2)
            return m.group(0) if repo == own_repo else f"`{repo}#{number}`"

        def shorthand(m: re.Match[str]) -> str:
            return m.group(0) if m.group(1) == own_repo else f"`{m.group(0)}`"

        segment = _LINKED_ITEM.sub(linked, segment)
        segment = _BARE_ITEM_URL.sub(url, segment)
        return _SHORTHAND.sub(shorthand, segment)

    return _outside_code(text, outside_code)


def qualify_bare_refs(text: str, repo: str) -> str:
    """`#123` in text copied from `repo` means `repo#123`; on the sandbox it would mean ours."""
    return _outside_code(text, lambda p: _BARE_REF.sub(lambda m: f"{repo}#{m.group(1)}", p))


def _outside_code(text: str, rewrite: Callable[[str], str]) -> str:
    """Apply `rewrite` to the prose only; code spans and fenced blocks pass through unchanged."""
    parts = _CODE.split(text)
    return "".join(p if i % 2 else rewrite(p) for i, p in enumerate(parts))


def safe_for_sandbox(text: str, own_repo: str) -> str:
    return inert_references(defuse_mentions(text), own_repo)
