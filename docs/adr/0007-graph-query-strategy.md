# ADR-0007: Fixed Cypher tools first, guarded text-to-Cypher fallback

**Status:** Accepted · **Date:** 2026-10-17 · **Decided by:** the team (Hinesh, Jignesh, Jaydeep, Het) · **Source:** [grilling round 1](../grilling/round-01.md), Q7

## Decision

The agent queries FalkorDB mainly through a curated set of **fixed, parameterised Cypher tools**, roughly one per hero question:

| Tool | Answers |
|---|---|
| `experts_for` | Who knows X? |
| `decision_trail` | Why was X decided? |
| `area_history` | What's the history of X? |
| `related_work` | What else does this touch? |
| `catch_up` | Catch me up on X since a date |
| `triage_candidates` | Duplicates, component and owner for a new issue |

Behind them sits a **text-to-Cypher fallback** for anything the tools don't cover. It is **read-only** (write clauses rejected), **size-limited** (forced `LIMIT`, query timeout), and its generated Cypher is shown to the user.

The same tools are exposed over **MCP**, so external agents such as Claude Code or Cursor can query the company brain.

## Why

Fixed tools are fast, correct and testable, and the rules require listing the queries the product depends on (Rule 10). The fallback shows flexibility without putting the demo at the mercy of generated queries.

## Consequences

- Each tool returns its **evidence path** (the matched graph path), not just an answer. Explainability is part of each tool's interface.
- Each tool's Cypher is documented in `docs/architecture/cypher-queries.md` and tested against a small fixture graph.
- Consider reusing FalkorDB's own `text-to-cypher` project for the fallback instead of building one.
