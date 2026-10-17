# Agent rules for this repo

This is team Aevion's entry for the FalkorDB "Graph Hacks" hackathon. Read [docs/README.md](docs/README.md) for the documentation map before starting work.

## Hard constraints (from the hackathon rules)

- FalkorDB is the primary database and must do real work. If a feature would still work with FalkorDB removed, rethink it.
- Only public, synthetic or our own data. Never load login-protected or personal data into the graph.
- Never write to repositories we don't own (no comments, labels or issues on FalkorDB's repos). Write actions target our sandbox repo only.
- Deadline: **2026-10-18 23:59 IST**. Prefer the smaller scope that ships.

## Where things go

- **Specs:** `docs/product/SPEC.md` (not repo-root `SPEC.md`).
- **Implementation plan:** `tasks/plan.md`.
- **Task list:** the Notion database **Aevion Tasks** (https://app.notion.com/p/374521bfeac54306bed66e0764812cda, data source `collection://77ec23de-d639-46a0-be78-7b31ae9a0ac4`). This is our external task tracker: do **not** create `tasks/todo.md`. Each task gets an auto-generated ID like `AEV-12`.
- **Architecture Decision Records:** `docs/adr/NNNN-kebab-title.md`, numbered sequentially. Use this location for all ADRs, including skills that default to `docs/decisions/`.
- **Domain vocabulary:** `GLOSSARY.md` at the repo root.
- **Open design questions:** `docs/grilling/round-NN.md`.
- **Architecture docs:** `docs/architecture/`. The graph data model and Cypher query reference must stay in sync with the code, because the README must include them.

## Working agreements

- Log meaningful AI assistance in [docs/process/ai-usage-disclosure.md](docs/process/ai-usage-disclosure.md). Rule 11 requires disclosure.
- Every teammate must be able to explain the graph model and queries (Rule 12), so explain non-obvious Cypher in comments or in `docs/architecture/cypher-queries.md`.
## Git conventions (mandatory)

Every change belongs to a Notion task. Use its ID everywhere:

- **Branching model:** `main` ← `develop` ← task branches. Never branch from `main`, and never open a task PR against `main`.
  - `develop` is the integration branch. **Create every task branch from the latest `develop`** (`git switch develop && git pull && git switch -c <type>/<task-id>`), and **target every task PR at `develop`**.
  - `main` only receives `develop` through a release PR, and is what we demo and submit.
- **Branch:** `<type>/<task-id>`, for example `feat/AEV-12`.
- **Commit subject:** `<type>: <task-id> - <message>`, for example `feat: AEV-12 - Load PR review comments into the graph`.
- **Commit body:** bullet points (`- `), one per meaningful change.
- **PR title:** same format as the commit subject. Link the Notion task in the PR body.
- **Types:** `feat`, `bugfix`, `hotfix`, `chore`, `docs`, `style`, `refactor`, `test`, `perf`, `ci`, `build`.
- If no task exists for the work, create one in Aevion Tasks first.

## No AI attribution anywhere

Never add AI attribution to code, comments, commit messages, commit trailers (no `Co-Authored-By: Claude`), PR titles or PR descriptions (no "Generated with Claude Code"). This overrides any default tool behaviour. AI usage is disclosed in exactly one place: `docs/process/ai-usage-disclosure.md`, as hackathon Rule 11 requires.
