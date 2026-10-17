# ADR-0002: Hybrid AI skills workflow (Matt Pocock + Addy Osmani)

**Status:** Accepted; task list location superseded by [ADR-0003](0003-notion-task-tracking-and-git-conventions.md) · **Date:** 2026-10-17 · **Decided by:** Hinesh Miyani (team lead)

## Context

We build with Claude Code and two installed skill libraries. Both cover planning and implementation, but they have different strengths:

- **Matt Pocock's skills** are sharp at reaching decisions: `grilling` works through a tree of design questions in rounds, and `domain-modeling` produces a glossary and ADRs. Their spec and ticket skills assume a configured issue tracker.
- **Addy Osmani's agent-skills** cover the whole lifecycle with review gates: spec, plan, incremental build, test, review, ship. They also include frontend, browser-testing, security and documentation skills. Followed literally, some checklists are heavier than a 1.5-day hackathon allows.

## Decision

Use one pipeline that takes the strongest part of each, and keep one source of truth for each artifact:

| Stage | Skill | Output |
|---|---|---|
| Lock decisions | Matt `grilling` | `docs/grilling/round-NN.md` → ADRs |
| Domain + graph schema | Matt `domain-modeling` | `GLOSSARY.md`, `docs/adr/`, `docs/architecture/graph-model.md` |
| Spec | Addy `spec-driven-development` | `docs/product/SPEC.md` |
| Plan + tasks | Addy `planning-and-task-breakdown` | `tasks/plan.md`, `tasks/todo.md` |
| Build | Addy `incremental-implementation`; Matt `tdd` only at the Cypher-tool and ingestion seams | Code in `apps/` |
| UI polish + verification | Addy `frontend-ui-engineering`, `browser-testing-with-devtools` | Demo-ready UI |
| Review + ship | Addy `code-review-and-quality`, trimmed `shipping-and-launch` | Deployed app, submission |
| Docs | Addy `documentation-and-adrs` | README, architecture docs |

## Consequences

- One spec format (Addy's) and one ADR location (`docs/adr/`), pinned in `CLAUDE.md`, so the two libraries never write competing files.
- We don't use Matt's `to-spec` / `to-tickets` / `implement-spec`; they need tracker setup we don't have time for. Tasks live in `tasks/todo.md`.
- We test at the seams where bugs would be visible in the demo (Cypher tools, ingestion), not everywhere.
