# Contributing

Team-internal guide for Aevion. Keep it short; we have a deadline.

## Before you start

1. Read [docs/hackathon/brief.md](docs/hackathon/brief.md) (5 min) and [CLAUDE.md](CLAUDE.md) (2 min).
2. Check the open grilling round in [docs/grilling/](docs/grilling/). If a decision you need is still open, answer it there; don't decide it silently in code.
3. Pick a task from the **[Aevion Tasks](https://app.notion.com/p/374521bfeac54306bed66e0764812cda)** board in Notion, assign yourself, and move it to **In Progress**. No task for your work? Create one first.

## Task flow (Notion)

`Backlog → To Do → In Progress → In Review → Done`. Use **Blocked** when you're waiting on someone, and say who in a Notion comment. Each task has an auto-generated ID such as `AEV-12`; that ID ties the branch, commits and PR back to the task.

## Branches

Format: `<type>/<task-id>`

```
feat/AEV-12
bugfix/AEV-19
docs/AEV-2
```

- `main` is always demo-able. Never push directly to it; merge through a PR.
- One branch per task.

## Commits

Subject: `<type>: <task-id> - <message>`, then a blank line, then a bullet-point body.

```
feat: AEV-12 - Load PR review comments into the graph

- Add REVIEWED relationship between Person and PullRequest
- Store review state and timestamp on the relationship
- Skip comments from bot accounts
```

**Types:** `feat`, `bugfix`, `hotfix`, `chore`, `docs`, `style`, `refactor`, `test`, `perf`, `ci`, `build`.

## Pull requests

- Title: same format as the commit subject, for example `feat: AEV-12 - Load PR review comments into the graph`.
- Body: fill in the PR template, including the Notion task link.
- At least one teammate reviews before merge. After merge, set the task to **Done** and paste the PR link into its **PR** field.

## No AI attribution

No AI attribution in code, commits (no `Co-Authored-By` trailers) or PRs (no "Generated with…" footers). If your assistant adds one, remove it. We disclose AI use once, in [docs/process/ai-usage-disclosure.md](docs/process/ai-usage-disclosure.md), because hackathon Rule 11 requires it.

## Where to put things

| Kind of thing | Location |
|---|---|
| Task | Notion: Aevion Tasks |
| Implementation plan | `tasks/plan.md` |
| Open question | `docs/grilling/round-NN.md` |
| Settled significant decision | `docs/adr/NNNN-title.md` |
| New domain term | `GLOSSARY.md` |
| Graph schema change | `docs/architecture/graph-model.md` **in the same PR** as the code |
| New or changed Cypher query | `docs/architecture/cypher-queries.md` **in the same PR** |
| Secrets | `.env` (git-ignored); add the variable name to `.env.example` |

## AI assistants

Allowed and encouraged. See [docs/process/ai-workflow.md](docs/process/ai-workflow.md).
