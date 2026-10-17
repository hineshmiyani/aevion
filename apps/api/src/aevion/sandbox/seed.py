"""Seed the sandbox with copies of real, open FalkorDB issues (ADR-0012, AEV-13).

The copies give the live triage demo realistic material. Each one says plainly that it is a
copy, names its original, and is made safe first (sandbox/safety.py): no @mentions, and every
reference to a FalkorDB issue or PR written as code, so nothing we post shows up on FalkorDB's
repos. A hidden marker records the original, so seeding again never makes duplicates.
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from aevion.graph.client import OrgGraph
from aevion.sandbox.safety import qualify_bare_refs, safe_for_sandbox
from aevion.sandbox.writer import SandboxWriter
from aevion.tools.scope import as_dicts

MIN_BODY_CHARS = 80
# The marker spells the key without "#", so GitHub can't read it as a reference either.
_MARKER = re.compile(r"<!-- aevion-copy-of: (\S+/\S+) issue (\d+) -->")

# Open issues with a real description, newest first.
SEED_CANDIDATES = """
MATCH (i:Issue)-[:IN_REPO]->(r:Repo)
WHERE i.state = 'OPEN' AND size(coalesce(i.body_excerpt, '')) > $min_chars
RETURN i.key AS key, i.title AS title, i.body_excerpt AS body, i.created_at AS created_at,
       r.full_name AS repo
ORDER BY i.created_at DESC
"""


@dataclass
class SeedReport:
    selected: int = 0
    created: int = 0
    already_there: int = 0


def pick(candidates: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    """A varied demo set: quotas by the square root of each repo's open issues (so the core repo
    leads without crowding out the rest), each quota spread across that repo's recent issues."""
    by_repo: dict[str, list[dict[str, Any]]] = {}
    for c in candidates:
        by_repo.setdefault(c["repo"], []).append(c)
    weight = {repo: len(issues) ** 0.5 for repo, issues in by_repo.items()}
    total = sum(weight.values()) or 1.0
    chosen: list[dict[str, Any]] = []
    for repo, issues in by_repo.items():
        quota = max(1, round(count * weight[repo] / total))
        recent = issues[: quota * 3]  # newest first; skip every other one or two for variety
        step = max(1, len(recent) // quota)
        chosen += recent[::step][:quota]
    chosen.sort(key=lambda c: c["created_at"] or 0, reverse=True)
    return chosen[:count]


def copy_body(issue: dict[str, Any], sandbox_repo: str) -> str:
    opened = (
        datetime.fromtimestamp(issue["created_at"] / 1000, UTC).strftime("%Y-%m-%d")
        if issue["created_at"]
        else "unknown date"
    )
    original_url = f"https://github.com/{issue['key'].replace('#', '/issues/')}"
    excerpt = safe_for_sandbox(qualify_bare_refs(issue["body"] or "", issue["repo"]), sandbox_repo)
    return (
        "> [!NOTE]\n"
        "> **A copy for the Aevion triage demo, not a real report.** "
        f"Original: `{issue['key']}` (`{original_url}`), opened {opened}.\n"
        "> FalkorDB references are written as code on purpose, so this sandbox never adds "
        '"mentioned this issue" events to FalkorDB\'s repos.\n\n'
        f"{excerpt.strip()}\n\n"
        "_This is an excerpt. The full report is on the original issue._\n\n"
        f"<!-- aevion-copy-of: {issue['key'].replace('#', ' issue ')} -->\n"
    )


def original_of(sandbox_issue: dict[str, Any]) -> str | None:
    match = _MARKER.search(sandbox_issue.get("body") or "")
    return f"{match.group(1)}#{match.group(2)}" if match else None


def seed(
    graph: OrgGraph, writer: SandboxWriter | None, count: int, *, dry_run: bool = False
) -> tuple[SeedReport, list[dict[str, Any]]]:
    candidates = as_dicts(graph.ro_query(SEED_CANDIDATES, {"min_chars": MIN_BODY_CHARS}))
    chosen = pick(candidates, count)
    report = SeedReport(selected=len(chosen))
    if dry_run or writer is None:
        return report, chosen
    existing = {original_of(i) for i in writer.issues()}
    for issue in chosen:
        if issue["key"] in existing:
            report.already_there += 1
            continue
        writer.create_issue(issue["title"], copy_body(issue, writer.repo))
        report.created += 1
    return report, chosen
