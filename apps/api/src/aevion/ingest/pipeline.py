"""Ingest one repo's pull requests into its org graph."""

from dataclasses import dataclass

from aevion.graph.client import OrgGraph
from aevion.ingest.github import GitHubClient
from aevion.ingest.loader import load_batch, upsert_repo
from aevion.ingest.normalize import Batch, pull_request_from
from aevion.ingest.org_config import OrgConfig


@dataclass
class RepoReport:
    repo: str
    pull_requests: int = 0
    people: int = 0
    file_changes: int = 0


def ingest_pull_requests(
    graph: OrgGraph, client: GitHubClient, config: OrgConfig, repo_name: str
) -> RepoReport:
    repo_config = config.repo(repo_name)
    report = RepoReport(repo=f"{config.org}/{repo_config.name}")
    for page in client.pull_request_pages(config.org, repo_config.name, config.since()):
        full_name = upsert_repo(graph, page)
        report.repo = full_name
        batch = Batch()
        for node in page["pullRequests"]["nodes"]:
            pr = pull_request_from(
                node, full_name, repo_config.component_depth, config.bot_logins, batch
            )
            report.file_changes += len(pr.files)
        load_batch(graph, batch)
        report.pull_requests += len(batch.pull_requests)
        report.people += len(batch.people)
    return report
