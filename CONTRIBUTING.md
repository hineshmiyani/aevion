# Contributing

Team-internal guide for Aevion. Keep it short; we have a deadline.

## Before you start

1. Read [docs/hackathon/brief.md](docs/hackathon/brief.md) (5 min) and [CLAUDE.md](CLAUDE.md) (2 min).
2. Check the open grilling round in [docs/grilling/](docs/grilling/). If a decision you need is still open, answer it there; don't decide it silently in code.
3. Pick a task from `tasks/todo.md` (once it exists) and put your name next to it.

## Branches and commits

- `main` is always demo-able. Never push broken code to it.
- Branch per task: `feat/<short-name>`, `fix/<short-name>`, `docs/<short-name>`.
- [Conventional Commits](https://www.conventionalcommits.org/): `feat(ingest): load PR review comments`.
- Small PRs; at least one teammate looks at each one before merging. Use the PR template.

## Where to put things

| Kind of thing | Location |
|---|---|
| Open question | `docs/grilling/round-NN.md` |
| Settled significant decision | `docs/adr/NNNN-title.md` |
| New domain term | `GLOSSARY.md` |
| Graph schema change | `docs/architecture/graph-model.md` **in the same PR** as the code |
| New or changed Cypher query | `docs/architecture/cypher-queries.md` **in the same PR** |
| Secrets | `.env` (git-ignored); add the variable name to `.env.example` |

## AI assistants

Allowed and encouraged. See [docs/process/ai-workflow.md](docs/process/ai-workflow.md), and log meaningful use in [docs/process/ai-usage-disclosure.md](docs/process/ai-usage-disclosure.md).
