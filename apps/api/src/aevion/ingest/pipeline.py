"""Ingest one repo's pull requests and issues into its org graph."""

from dataclasses import dataclass

from aevion.graph.client import OrgGraph
from aevion.ingest.github import GitHubClient
from aevion.ingest.loader import load_batch, upsert_repo
from aevion.ingest.normalize import Batch, issue_from, pull_request_from
from aevion.ingest.org_config import OrgConfig


@dataclass
class RepoReport:
    repo: str
    pull_requests: int = 0
    issues: int = 0
    comments: int = 0
    file_changes: int = 0


def ingest_repo(graph: OrgGraph, client: GitHubClient, config: OrgConfig, name: str) -> RepoReport:
    repo_config = config.repo(name)
    since = config.since()
    report = RepoReport(repo=f"{config.org}/{repo_config.name}")

    for page in client.pull_request_pages(config.org, repo_config.name, since):
        report.repo = upsert_repo(graph, page)
        batch = Batch()
        for node in page["pullRequests"]["nodes"]:
            pr = pull_request_from(
                node, report.repo, repo_config.component_depth, config.bot_logins, batch
            )
            report.file_changes += len(pr.files)
        load_batch(graph, batch)
        report.pull_requests += len(batch.pull_requests)
        report.comments += len(batch.comments)

    for page in client.issue_pages(config.org, repo_config.name, since):
        report.repo = upsert_repo(graph, page)
        batch = Batch()
        for node in page["issues"]["nodes"]:
            issue_from(node, report.repo, config.bot_logins, batch)
        load_batch(graph, batch)
        report.issues += len(batch.issues)
        report.comments += len(batch.comments)

    return report
