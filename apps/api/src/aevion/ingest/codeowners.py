"""CODEOWNERS parsing (GLOSSARY: Owner). Owners are who *should* review a Component;
Experts (experts_for) are who actually works on it. Showing both is the point.

Only directory-shaped patterns map to a Component. Global patterns such as `*` or `*.md`
don't name a part of the codebase, so they are skipped.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from aevion.ingest.components import ROOT_COMPONENT, component_path

CODEOWNERS_PATHS = (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS")
_GLOB = set("*?[")


@dataclass(frozen=True)
class OwnerRule:
    pattern: str
    owners: tuple[str, ...]  # "@user", "@org/team" or an email


def parse_codeowners(text: str) -> list[OwnerRule]:
    rules: list[OwnerRule] = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        pattern, *owners = line.split()
        if owners:
            rules.append(OwnerRule(pattern, tuple(owners)))
    return rules


def pattern_component_path(pattern: str, depth: int) -> str | None:
    """The Component a CODEOWNERS pattern points at, or None for global patterns.

    >>> pattern_component_path("/src/execution_plan/", 2)
    'src/execution_plan'
    >>> pattern_component_path("/build/", 2)
    'build'
    >>> pattern_component_path("docs/**/*.md", 1)
    'docs'
    >>> pattern_component_path("*.md", 2) is None
    True
    """
    path = pattern.strip("/")
    directories: list[str] = []
    for part in path.split("/"):
        if not part or any(ch in _GLOB for ch in part):
            break
        directories.append(part)
    else:
        if not pattern.endswith("/") and directories:
            directories = directories[:-1]  # a file pattern like /CODEOWNERS or /src/x.c
    if not directories:
        return None if any(ch in _GLOB for ch in path) else ROOT_COMPONENT
    return component_path("/".join(directories) + "/_", depth)


def owner_kind(owner: str) -> str | None:
    """'team' for @org/team, 'person' for @user; emails can't be matched to logins."""
    if not owner.startswith("@"):
        return None
    return "team" if "/" in owner else "person"


@dataclass(frozen=True)
class Ownership:
    owner: str  # login for people, "org/team" for teams (no leading @)
    kind: str  # "person" | "team"
    component_path: str
    valid_from: int | None
    valid_to: int | None  # None while the rule is still in the current CODEOWNERS


def ownership_intervals(versions: Sequence[tuple[int | None, str]], depth: int) -> list[Ownership]:
    """Turn CODEOWNERS versions (oldest first) into time-ranged ownerships.

    An owner/Component pair is valid from the version that adds it until the version that
    removes it; pairs present in the latest version stay open (`valid_to = None`).
    """
    open_since: dict[tuple[str, str, str], int | None] = {}
    closed: list[Ownership] = []
    for at, text in versions:
        current = set()
        for rule in parse_codeowners(text):
            path = pattern_component_path(rule.pattern, depth)
            if path is None:
                continue
            for owner in rule.owners:
                kind = owner_kind(owner)
                if kind:
                    current.add((owner.lstrip("@"), kind, path))
        for pair in list(open_since):
            if pair not in current:
                closed.append(Ownership(*pair, valid_from=open_since.pop(pair), valid_to=at))
        for pair in current:
            open_since.setdefault(pair, at)
    still_open = [
        Ownership(*pair, valid_from=since, valid_to=None) for pair, since in open_since.items()
    ]
    return sorted(closed + still_open, key=lambda o: (o.component_path, o.owner, o.valid_from or 0))
