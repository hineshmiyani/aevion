"""Turn raw GitHub GraphQL nodes into plain records for the loader. Pure functions only."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aevion.ingest.components import component_key, component_path, is_doc
from aevion.ingest.references import find_closing_references, find_references

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
class LabelRec:
    key: str
    repo: str
    name: str
    color: str | None


@dataclass(frozen=True)
class CommentRec:
    """`kind`: issue (conversation), review (review summary) or review_thread (inline)."""

    id: str
    kind: str
    excerpt: str
    url: str
    created_at: int | None
    author: str
    thread_key: str


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
    reviews: tuple[ReviewRec, ...] = ()
    files: tuple[FileChangeRec, ...] = ()
    labels: tuple[str, ...] = ()
    ref_keys: tuple[str, ...] = ()
    fix_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class IssueRec:
    key: str
    repo: str
    number: int
    title: str
    body_excerpt: str
    state: str
    url: str
    created_at: int | None
    closed_at: int | None
    updated_at: int | None
    author: str | None
    labels: tuple[str, ...] = ()
    assignees: tuple[str, ...] = ()
    ref_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReleaseRec:
    key: str
    repo: str
    tag: str
    name: str
    url: str
    published_at: int | None
    pr_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class OwnsRec:
    owner: str
    kind: str  # "person" | "team"
    repo: str
    component_key: str
    component_path: str
    valid_from: int  # 0 when the first version's date is unknown
    valid_to: int | None


@dataclass
class Batch:
    """Everything one ingestion page produced, deduplicated by key."""

    people: dict[str, PersonRec] = field(default_factory=dict)
    labels: dict[str, LabelRec] = field(default_factory=dict)
    pull_requests: list[PullRequestRec] = field(default_factory=list)
    issues: list[IssueRec] = field(default_factory=list)
    comments: list[CommentRec] = field(default_factory=list)
    releases: list[ReleaseRec] = field(default_factory=list)
    ownerships: list[OwnsRec] = field(default_factory=list)

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
    key = f"{repo}#{node['number']}"
    author = person_from(node.get("author"), bot_logins)
    batch.add_person(author)

    reviews: list[ReviewRec] = []
    review_texts: list[str] = []
    for review in _nodes(node, "reviews"):
        reviewer = person_from(review.get("author"), bot_logins)
        if reviewer is None:
            continue
        batch.add_person(reviewer)
        reviews.append(
            ReviewRec(reviewer.login, review["state"], to_epoch_ms(review.get("submittedAt")))
        )
        if reviewer.is_bot:
            continue  # AI review bots post long summaries: noise for expertise and decisions
        if review.get("body"):
            review_texts.append(review["body"])
            _add_comment(batch, review, "rv", "review", reviewer.login, key)
        for inline in _nodes(review, "comments"):
            review_texts.append(inline.get("body") or "")
            _add_comment(batch, inline, "rc", "review_thread", reviewer.login, key)

    conversation = _thread_comments(node, key, bot_logins, batch)

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
        for f in _nodes(node, "files")
    )

    body = node.get("body") or ""
    fixes = find_closing_references(body, repo) | {
        f"{ref['repository']['nameWithOwner']}#{ref['number']}"
        for ref in _nodes(node, "closingIssuesReferences")
    }
    refs = _references([body, node.get("title"), *conversation, *review_texts], repo) - fixes

    record = PullRequestRec(
        key=key,
        repo=repo,
        number=int(node["number"]),
        title=node.get("title") or "",
        body_excerpt=body[:BODY_EXCERPT_CHARS],
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
        labels=_labels(node, repo, batch),
        ref_keys=tuple(sorted(refs - {key})),
        fix_keys=tuple(sorted(fixes - {key})),
    )
    batch.pull_requests.append(record)
    return record


def issue_from(
    node: dict[str, Any], repo: str, bot_logins: frozenset[str], batch: Batch
) -> IssueRec:
    key = f"{repo}#{node['number']}"
    author = person_from(node.get("author"), bot_logins)
    batch.add_person(author)

    assignees: list[str] = []
    for actor in _nodes(node, "assignees"):
        person = person_from({"__typename": "User", **actor}, bot_logins)
        if person:
            batch.add_person(person)
            assignees.append(person.login)

    conversation = _thread_comments(node, key, bot_logins, batch)
    body = node.get("body") or ""
    refs = _references([body, node.get("title"), *conversation], repo) - {key}

    record = IssueRec(
        key=key,
        repo=repo,
        number=int(node["number"]),
        title=node.get("title") or "",
        body_excerpt=body[:BODY_EXCERPT_CHARS],
        state=node["state"],
        url=node["url"],
        created_at=to_epoch_ms(node.get("createdAt")),
        closed_at=to_epoch_ms(node.get("closedAt")),
        updated_at=to_epoch_ms(node.get("updatedAt")),
        author=author.login if author else None,
        labels=_labels(node, repo, batch),
        assignees=tuple(assignees),
        ref_keys=tuple(sorted(refs)),
    )
    batch.issues.append(record)
    return record


def release_from(node: dict[str, Any], repo: str, batch: Batch) -> ReleaseRec:
    """Release notes list the PRs they ship ("Fix crash (#3176)"): those become INCLUDES."""
    record = ReleaseRec(
        key=f"{repo}@{node['tagName']}",
        repo=repo,
        tag=node["tagName"],
        name=node.get("name") or node["tagName"],
        url=node["url"],
        published_at=to_epoch_ms(node.get("publishedAt")),
        pr_keys=tuple(sorted(find_references(node.get("description"), repo))),
    )
    batch.releases.append(record)
    return record


def ownerships_from(
    versions: list[tuple[str | None, str]], repo: str, component_depth: int, batch: Batch
) -> None:
    from aevion.ingest.codeowners import ownership_intervals

    for own in ownership_intervals(
        [(to_epoch_ms(at), text) for at, text in versions], component_depth
    ):
        batch.ownerships.append(
            OwnsRec(
                owner=own.owner,
                kind=own.kind,
                repo=repo,
                component_key=f"{repo}:{own.component_path}",
                component_path=own.component_path,
                valid_from=own.valid_from or 0,
                valid_to=own.valid_to,
            )
        )


def _nodes(parent: dict[str, Any], connection: str) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = (parent.get(connection) or {}).get("nodes") or []
    return nodes


def _thread_comments(
    node: dict[str, Any], thread_key: str, bot_logins: frozenset[str], batch: Batch
) -> list[str]:
    """Add human conversation comments to the batch; return their texts for reference parsing."""
    texts: list[str] = []
    for comment in _nodes(node, "comments"):
        author = person_from(comment.get("author"), bot_logins)
        if author is None or author.is_bot:
            continue
        batch.add_person(author)
        texts.append(comment.get("body") or "")
        _add_comment(batch, comment, "ic", "issue", author.login, thread_key)
    return texts


def _add_comment(
    batch: Batch, raw: dict[str, Any], prefix: str, kind: str, author: str, thread_key: str
) -> None:
    if not raw.get("databaseId") or not raw.get("url"):
        return
    batch.comments.append(
        CommentRec(
            id=f"{prefix}:{raw['databaseId']}",  # GitHub ID spaces differ per comment type
            kind=kind,
            excerpt=(raw.get("body") or "")[:BODY_EXCERPT_CHARS],
            url=raw["url"],
            created_at=to_epoch_ms(raw.get("createdAt") or raw.get("submittedAt")),
            author=author,
            thread_key=thread_key,
        )
    )


def _labels(node: dict[str, Any], repo: str, batch: Batch) -> tuple[str, ...]:
    keys: list[str] = []
    for label in _nodes(node, "labels"):
        rec = LabelRec(f"{repo}:{label['name']}", repo, label["name"], label.get("color"))
        batch.labels.setdefault(rec.key, rec)
        keys.append(rec.key)
    return tuple(keys)


def _references(texts: Iterable[str | None], repo: str) -> set[str]:
    refs: set[str] = set()
    for text in texts:
        refs |= find_references(text, repo)
    return refs


def _latest_review_per_person(reviews: list[ReviewRec]) -> list[ReviewRec]:
    """One REVIEWED edge per person and PR, carrying their most recent review state."""
    latest: dict[str, ReviewRec] = {}
    for review in reviews:
        current = latest.get(review.login)
        if current is None or (review.at or 0) >= (current.at or 0):
            latest[review.login] = review
    return list(latest.values())
