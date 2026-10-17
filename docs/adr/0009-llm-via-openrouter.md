# ADR-0009: Claude Sonnet 5.5 + Haiku 5.5 through OpenRouter, on a $16 budget

**Status:** Accepted; model choice superseded by [ADR-0010](0010-llm-model-bake-off.md) (OpenRouter access and guardrails still apply) · **Date:** 2026-10-17 · **Decided by:** the team (Hinesh, Jignesh, Jaydeep, Het) · **Source:** [grilling round 1](../grilling/round-01.md), Q9

## Decision

- **Agent reasoning and tool use:** `anthropic/claude-sonnet-5.5`
- **Bulk extraction** (decisions, topics, components from PR and issue threads): `anthropic/claude-haiku-5.5`, using the `:batch` variant where latency doesn't matter
- **Access:** OpenRouter's API, not a direct Anthropic key. The team has **$16 of OpenRouter credit**.

## Budget

OpenRouter prices checked 2026-10-17 (per million tokens):

| Model | Input | Output |
|---|---|---|
| claude-haiku-5.5 | $0.10 | $0.50 |
| claude-haiku-5.5:batch | $0.05 | $0.25 |
| claude-sonnet-5.5 | $2.00 | $10.00 |

Estimates:

- Extracting from all ~10k threads (~3k tokens in, ~300 out each) would cost about **$4.50**, or **$2.25** batched.
- Each agent answer (~15k tokens in, ~1k out) costs about **$0.04**, so 200 answers cost about **$8**.

Together that fits in $16, but not with careless development or an unprotected public demo.

## Guardrails (required)

1. **Deterministic edges first.** Authorship, reviews, file changes, `#123` / `fixes #123` references and CODEOWNERS come from GitHub data with no LLM. Only threads likely to contain decisions go to Haiku.
2. **Cache every LLM result** by content hash, so re-running ingestion is free.
3. **Dry-run cost estimate** before any full extraction run: count tokens, print the projected cost, and require confirmation.
4. **Develop against cheap models.** See ADR-0010 for how the demo model is chosen.
5. **Protect the public deployment:** rate-limit per IP, cap answer length, and pre-compute the demo's hero answers so judges clicking around can't drain the credit.
6. **Set a credit limit on the OpenRouter key** so a bug can't spend everything.

## Consequences

- We call OpenRouter's OpenAI-compatible API, so the client code uses that interface rather than the Anthropic SDK.
- Model IDs live in configuration, so switching to a direct Anthropic key later only needs a config change.
- The OpenRouter key lives only in `.env` (git-ignored) and the deployment's secret store.
