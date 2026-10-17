"""Build the LLM client from settings, so callers never handle keys or paths."""

from aevion.config import Settings
from aevion.llm.client import Ledger, LLMClient


def ledger_for(settings: Settings) -> Ledger:
    return Ledger(settings.llm_data_dir / "ledger.jsonl")


def llm_client(settings: Settings) -> LLMClient:
    return LLMClient(
        settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        cache_dir=settings.llm_data_dir / "cache",
        ledger=ledger_for(settings),
        budget_usd=settings.llm_budget_usd,
    )
