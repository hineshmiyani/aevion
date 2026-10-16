# Agent rules for this repo

This is team Aevion's entry for the FalkorDB "Graph Hacks" hackathon. Read [docs/README.md](docs/README.md) for the documentation map before starting work.

## Hard constraints (from the hackathon rules)

- FalkorDB is the primary database and must do real work. If a feature would still work with FalkorDB removed, rethink it.
- Only public, synthetic or our own data. Never load login-protected or personal data into the graph.
- Never write to repositories we don't own (no comments, labels or issues on FalkorDB's repos). Write actions target our sandbox repo only.
- Deadline: **2026-10-18 23:59 IST**. Prefer the smaller scope that ships.

## Where things go

- **Specs:** `docs/product/SPEC.md` (not repo-root `SPEC.md`).
- **Implementation plan and task list:** `tasks/plan.md` and `tasks/todo.md`.
- **Architecture Decision Records:** `docs/adr/NNNN-kebab-title.md`, numbered sequentially. Use this location for all ADRs, including skills that default to `docs/decisions/`.
- **Domain vocabulary:** `GLOSSARY.md` at the repo root.
- **Open design questions:** `docs/grilling/round-NN.md`.
- **Architecture docs:** `docs/architecture/`. The graph data model and Cypher query reference must stay in sync with the code, because the README must include them.

## Working agreements

- Log meaningful AI assistance in [docs/process/ai-usage-disclosure.md](docs/process/ai-usage-disclosure.md). Rule 11 requires disclosure.
- Every teammate must be able to explain the graph model and queries (Rule 12), so explain non-obvious Cypher in comments or in `docs/architecture/cypher-queries.md`.
- Commit messages follow Conventional Commits. Do not add AI attribution trailers.
