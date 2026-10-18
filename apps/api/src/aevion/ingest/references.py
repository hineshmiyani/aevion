"""Find issue/PR references in GitHub text: `#12`, `owner/repo#12` and full GitHub URLs.

Closing keywords ("fixes #12") become FIXES edges; every other mention becomes REFERENCES.
GitHub numbers issues and PRs from one sequence per repo, so `owner/repo#n` identifies
exactly one Issue or PullRequest.
"""

import re

_REPO = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9._-]{1,100}"
_URL = re.compile(rf"https://github\.com/({_REPO})/(?:issues|pull)/(\d+)\b")
_MENTION = re.compile(rf"(?<![\w/#])(?:({_REPO}))?#(\d+)\b")
_CLOSING = re.compile(
    rf"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*:?\s+"
    rf"(?:https://github\.com/({_REPO})/(?:issues|pull)/(\d+)|(?:({_REPO}))?#(\d+))",
    re.IGNORECASE,
)
_CODE = re.compile(r"```.*?```|`[^`\n]*`", re.DOTALL)


def _strip_code(text: str) -> str:
    """`#123` inside code is usually a colour, a line number or a comment, not a reference."""
    return _CODE.sub(" ", text)


def find_references(text: str | None, repo: str) -> set[str]:
    """Keys (`owner/repo#n`) of every issue or PR mentioned in `text`."""
    if not text:
        return set()
    clean = _strip_code(text)
    keys = {f"{r}#{n}" for r, n in _URL.findall(clean)}
    keys |= {f"{r or repo}#{n}" for r, n in _MENTION.findall(_URL.sub(" ", clean))}
    return keys


def find_closing_references(text: str | None, repo: str) -> set[str]:
    """Keys of issues a PR says it closes ("Fixes #12", "resolves owner/repo#3")."""
    if not text:
        return set()
    keys: set[str] = set()
    for url_repo, url_number, mention_repo, mention_number in _CLOSING.findall(_strip_code(text)):
        if url_number:
            keys.add(f"{url_repo}#{url_number}")
        else:
            keys.add(f"{mention_repo or repo}#{mention_number}")
    return keys
