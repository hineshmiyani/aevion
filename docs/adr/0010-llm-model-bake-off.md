# ADR-0010: Develop on cheap models; pick final models with a bake-off

**Status:** Accepted · **Date:** 2026-10-17 · **Decided by:** Hinesh Miyani · **Partly supersedes:** the model choice in [ADR-0009](0009-llm-via-openrouter.md) (OpenRouter access and the budget guardrails still stand)

## Context

ADR-0009 fixed Claude Sonnet 5.5 (agent) and Haiku 5.5 (extraction) on a $16 OpenRouter budget. OpenRouter also offers Kimi, GLM, DeepSeek and Qwen models with tool calling, several of them 2–20× cheaper per task. Prices alone don't show whether they give equivalent output on our tasks: choosing the right Cypher tool, and extracting decisions accurately from PR threads.

Cost per task on OpenRouter, checked 2026-10-17:

**Extraction**: a full run over ~10k threads (30M tokens in, 3M out).

| Model | Cost |
|---|---|
| claude-haiku-5.5 | $4.50 ($2.25 batched) |
| deepseek-v4.1-flash | $3.30 ($1.95 batched) |
| glm-5.3-flash (batched) | $2.04 |
| qwen3.7-flash | $1.29 |

**Agent**: one answer (15k tokens in, 1k out).

| Model | Per answer | With 3k reasoning tokens |
|---|---|---|
| claude-sonnet-5.5 | $0.040 | $0.070 |
| kimi-k3 | $0.017 | $0.052 |
| deepseek-v4-pro-0813 | $0.012 | $0.018 |
| glm-5.3 | $0.006 | $0.020 |
| claude-haiku-5.5 | $0.002 | $0.004 |

Reasoning models bill hidden thinking tokens as output. That is why Kimi K3, with output at $11.94 per million tokens, can cost more per answer than Sonnet.

## Decision

1. **During development**, use `anthropic/claude-haiku-5.5` or `z-ai/glm-5.3-flash` for both the agent and extraction. Development traffic costs almost nothing.
2. **Run a bake-off once ingestion has real data** (Notion task "Run LLM model bake-off on real graph data"). Total cost: under $1.
   - **Extraction test:** 20 PR/issue threads where we've written down the correct decision, topics and component. Candidates: Haiku 5.5, DeepSeek V4.1 Flash, GLM-5.3 Flash, Qwen 3.7 Flash.
   - **Agent test:** 10 known-answer questions covering all five question types plus triage. Score whether the right tool was called with the right parameters, whether the answer is correct, and whether the evidence path is valid. Also measure latency. Candidates: Sonnet 5.5, Haiku 5.5, GLM-5.3, DeepSeek V4 Pro.
3. **Pick** the extraction model and the agent (demo) model from the results, and record the choice in a follow-up ADR. Results go in `docs/architecture/model-bakeoff.md`.

## Consequences

- Model IDs must live in configuration (`EXTRACTION_MODEL`, `AGENT_MODEL`), never hard-coded, so switching is a config change.
- The LLM client uses OpenRouter's OpenAI-compatible API, so all candidates work through one code path, including tool calling.
- The labelled threads and known-answer questions become a regression set for prompt and tool changes after the bake-off.
- The bake-off results table goes in the README, as evidence of our technical choices (Rule 12).
- When comparing reasoning models, count reasoning tokens in the cost, and cap or disable reasoning where the provider allows.
