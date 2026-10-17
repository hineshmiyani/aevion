"""Turn raw GitHub GraphQL nodes into plain records for the loader. Pure functions only."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aevion.ingest.components import component_key, component_path, is_doc

BODY_EXCERPT_CHARS = 500


@dataclass(frozen=True)
class PersonRec:
    login: str
    is_bot: bool
    avatar_url: str | None = None


@dataclass(frozen=True)
class ReviewRec:
    login: str
    state: str
    at: int | None


@dataclass(frozen=True)
class FileChangeRec:
    file_key: str
    path: str
    is_doc: bool
    component_key: str
    component_path: str
    additions: int
    deletions: int


@dataclass(frozen=True)
class PullRequestRec:
    key: str
    repo: str
    number: int
    title: str
    body_excerpt: str
    state: str
    url: str
    created_at: int | None
    merged_at: int | None
    closed_at: int | None
    updated_at: int | None
    additions: int
    deletions: int
    author: str | None
    reviews: tuple[ReviewRec, ...] = field(default_factory=tuple)
    files: tuple[FileChangeRec, ...] = field(default_factory=tuple)


@dataclass
class Batch:
    """Everything one ingestion page produced, deduplicated by key."""

    people: dict[str, PersonRec] = field(default_factory=dict)
    pull_requests: list[PullRequestRec] = field(default_factory=list)

    def add_person(self, person: PersonRec | None) -> None:
        if person and person.login not in self.people:
            self.people[person.login] = person


def to_epoch_ms(value: str | None) -> int | None:
    if not value:
        return None
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


def person_from(actor: dict[str, Any] | None, bot_logins: frozenset[str]) -> PersonRec | None:
    """GitHub returns `author: null` for deleted accounts ("ghost"); those are skipped."""
    if not actor or not actor.get("login"):
        return None
    login: str = actor["login"]
    is_bot = (
        actor.get("__typename") == "Bot"
        or login.lower().endswith("[bot]")
        or login.lower() in bot_logins
    )
    return PersonRec(login=login, is_bot=is_bot, avatar_url=actor.get("avatarUrl"))


def pull_request_from(
    node: dict[str, Any],
    repo: str,
    component_depth: int,
    bot_logins: frozenset[str],
    batch: Batch,
) -> PullRequestRec:
    author = person_from(node.get("author"), bot_logins)
    batch.add_person(author)

    reviews: list[ReviewRec] = []
    for review in (node.get("reviews") or {}).get("nodes", []):
        reviewer = person_from(review.get("author"), bot_logins)
        if reviewer is None:
            continue
        batch.add_person(reviewer)
        reviews.append(
            ReviewRec(reviewer.login, review["state"], to_epoch_ms(review.get("submittedAt")))
        )

    files = tuple(
        FileChangeRec(
            file_key=f"{repo}:{f['path']}",
            path=f["path"],
            is_doc=is_doc(f["path"]),
            component_key=component_key(repo, f["path"], component_depth),
            component_path=component_path(f["path"], component_depth),
            additions=int(f.get("additions") or 0),
            deletions=int(f.get("deletions") or 0),
        )
        for f in (node.get("files") or {}).get("nodes", [])
    )

    record = PullRequestRec(
        key=f"{repo}#{node['number']}",
        repo=repo,
        number=int(node["number"]),
        title=node.get("title") or "",
        body_excerpt=(node.get("body") or "")[:BODY_EXCERPT_CHARS],
        state=node["state"],
        url=node["url"],
        created_at=to_epoch_ms(node.get("createdAt")),
        merged_at=to_epoch_ms(node.get("mergedAt")),
        closed_at=to_epoch_ms(node.get("closedAt")),
        updated_at=to_epoch_ms(node.get("updatedAt")),
        additions=int(node.get("additions") or 0),
        deletions=int(node.get("deletions") or 0),
        author=author.login if author else None,
        reviews=tuple(_latest_review_per_person(reviews)),
        files=files,
    )
    batch.pull_requests.append(record)
    return record


def _latest_review_per_person(reviews: list[ReviewRec]) -> list[ReviewRec]:
    """One REVIEWED edge per person and PR, carrying their most recent review state."""
    latest: dict[str, ReviewRec] = {}
    for review in reviews:
        current = latest.get(review.login)
        if current is None or (review.at or 0) >= (current.at or 0):
            latest[review.login] = review
    return list(latest.values())
