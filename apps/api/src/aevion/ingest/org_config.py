"""Per-org ingestion config, read from config/orgs/<org>.toml."""

import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path


@dataclass(frozen=True)
class RepoConfig:
    name: str
    component_depth: int


@dataclass(frozen=True)
class OrgConfig:
    org: str
    since_months: int
    repos: tuple[RepoConfig, ...]
    bot_logins: frozenset[str]

    def since(self, now: datetime | None = None) -> datetime:
        return (now or datetime.now(UTC)) - timedelta(days=30 * self.since_months)

    def repo(self, name: str) -> RepoConfig:
        for repo in self.repos:
            if repo.name.lower() == name.lower():
                return repo
        raise KeyError(f"{name!r} is not configured for {self.org}")


def load_org_config(path: Path) -> OrgConfig:
    data = tomllib.loads(path.read_text())
    default_depth = int(data.get("component_depth", 2))
    return OrgConfig(
        org=data["org"],
        since_months=int(data.get("since_months", 12)),
        repos=tuple(
            RepoConfig(name=r["name"], component_depth=int(r.get("component_depth", default_depth)))
            for r in data["repos"]
        ),
        bot_logins=frozenset(login.lower() for login in data.get("bot_logins", [])),
    )
