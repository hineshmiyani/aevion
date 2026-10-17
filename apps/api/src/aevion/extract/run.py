"""Run decision extraction over all candidate threads, or price it first with a dry run."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

import httpx

from aevion.extract.candidates import candidates, load_thread
from aevion.extract.extractor import DecisionRec, estimate_tokens, extract_decisions
from aevion.extract.loader import link_supersedes, load_decisions
from aevion.graph.client import OrgGraph
from aevion.llm.client import BudgetExceededError, LLMClient, LLMError

OUTPUT_TOKENS_PER_THREAD = 250  # observed upper range for the JSON reply


@dataclass
class DryRun:
    threads: int
    input_tokens: int
    output_tokens: int
    usd: float | None  # None when pricing couldn't be fetched


@dataclass
class RunReport:
    threads: int = 0
    decisions: int = 0
    dropped_low_confidence: int = 0
    invalid_json: int = 0
    errors: list[str] = field(default_factory=list)
    stopped_on_budget: bool = False


def model_pricing(model: str, base_url: str) -> tuple[float, float] | None:
    """(input, output) USD per token from OpenRouter's public model list."""
    try:
        models = httpx.get(f"{base_url.rstrip('/')}/models", timeout=20).json()["data"]
    except (httpx.HTTPError, KeyError, ValueError):
        return None
    for m in models:
        if m.get("id") == model:
            pricing = m.get("pricing", {})
            return float(pricing.get("prompt", 0)), float(pricing.get("completion", 0))
    return None


def dry_run(
    graph: OrgGraph, model: str, base_url: str, repo: str | None, limit: int | None
) -> DryRun:
    picked = candidates(graph, repo)[:limit]
    input_tokens = sum(estimate_tokens(load_thread(graph, k, label)) for k, label in picked)
    output_tokens = OUTPUT_TOKENS_PER_THREAD * len(picked)
    pricing = model_pricing(model, base_url)
    usd = None if pricing is None else input_tokens * pricing[0] + output_tokens * pricing[1]
    return DryRun(len(picked), input_tokens, output_tokens, usd)


def run_extraction(
    graph: OrgGraph,
    client: LLMClient,
    model: str,
    repo: str | None,
    limit: int | None,
    workers: int = 8,
) -> RunReport:
    report = RunReport()
    picked = candidates(graph, repo)[:limit]
    threads = [load_thread(graph, key, label) for key, label in picked]
    report.threads = len(threads)

    found: list[DecisionRec] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(extract_decisions, client, model, t): t for t in threads}
        for future in as_completed(futures):
            thread = futures[future]
            try:
                result = future.result()
            except BudgetExceededError:
                report.stopped_on_budget = True
                continue
            except LLMError as exc:
                report.errors.append(f"{thread.key}: {exc}")
                continue
            found.extend(result.decisions)
            report.dropped_low_confidence += result.dropped
            report.invalid_json += int(result.invalid_json)

    load_decisions(graph, found)  # one write pass, after all model calls
    link_supersedes(graph)
    report.decisions = len(found)
    return report
