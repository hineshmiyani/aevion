# ADR-0003: Notion for task tracking; task IDs in branches and commits

**Status:** Accepted · **Date:** 2026-10-17 · **Decided by:** Hinesh Miyani (team lead) · **Supersedes:** the `tasks/todo.md` task list in [ADR-0002](0002-hybrid-ai-skills-workflow.md)

## Context

Three people will work in parallel for about 1.5 days. A markdown checklist in the repo (`tasks/todo.md`) leads to merge conflicts when everyone updates it, and it has no assignees, statuses or board view. The team already uses Notion.

## Decision

1. **Tasks live in the Notion database "Aevion Tasks"**, used like JIRA: Status (Backlog → To Do → In Progress → In Review → Done, plus Blocked), Type, Priority, Assignee, Area, Phase, Estimate, Due, Acceptance criteria, and PR link. Each task gets an auto-generated ID with prefix `AEV` (for example `AEV-12`).
2. **Branching model:** `main` ← `develop` ← task branches. Task branches are created from `develop` and their PRs target `develop`. `main` only receives `develop` through release PRs, and is what we demo and submit.
3. **Branch names:** `<type>/<task-id>`, for example `feat/AEV-12`.
4. **Commit subjects:** `<type>: <task-id> - <message>`, with a bullet-point body.
5. **Types:** `feat`, `bugfix`, `hotfix`, `chore`, `docs`, `style`, `refactor`, `test`, `perf`, `ci`, `build`.
6. **Merge commits only** (added 2026-10-17, AEV-41): task PRs are merged with a two-parent merge commit whose subject follows the commit format plus `(#n)`. Squash merging is disabled on the repo and rebase merging must not be used, because both cut the link between a task branch and `develop`. The first nine merges were rebuilt as merge commits the same day.
7. **No AI attribution** in code, commits or PRs. AI use is disclosed only in `docs/process/ai-usage-disclosure.md` (hackathon Rule 11).

`tasks/plan.md` remains the plan document. Addy Osmani's planning skill supports an external tracker when the project's agent rules name one, so `CLAUDE.md` names the Notion database.

## Consequences

- Every commit and branch can be traced to a task, and every task to its PR.
- Teammates need edit access to the Notion page, which is shared from Notion separately from GitHub.
- The commit subject differs from strict Conventional Commits (`type: ID - message` rather than `type(scope): message`), so commitlint-style tooling would need a custom rule if we add it.
- The first commit on `main` (`3455540`) predates this convention and is tracked retroactively as AEV-1.
