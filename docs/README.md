# Documentation map

Every planning, design and process document lives here, grouped by purpose. Code docs (setup, API) will live next to the code in `apps/` once it exists.

```
.
├── README.md                  Project front door (judges + teammates)
├── CLAUDE.md                  Rules for AI coding agents working in this repo
├── AGENTS.md                  Pointer to CLAUDE.md for non-Claude agents
├── CONTRIBUTING.md            How we work: branches, commits, PRs, tasks
├── GLOSSARY.md                Domain vocabulary (created during domain modeling)
├── docs/
│   ├── hackathon/             The event: rules, deadline, what to submit
│   ├── research/              Analysis that led to our choices
│   ├── grilling/              Open design questions, one file per round
│   ├── adr/                   Accepted decisions (Architecture Decision Records)
│   ├── product/               SPEC.md: what we build and how we know it's done
│   ├── architecture/          System design, graph data model, Cypher reference
│   └── process/               AI workflow and AI-usage disclosure
├── tasks/                     plan.md (implementation plan; tasks themselves live in Notion)
└── apps/ · infra/             Code (created once the stack is locked)
```

## Lifecycle of a decision

1. **Open question** → added to the current round in `docs/grilling/round-NN.md`, with a recommended answer.
2. **Answered** → the round file records the answer and who decided.
3. **Significant and settled** → written up as an ADR in `docs/adr/NNNN-title.md`.
4. **Changed later** → a new ADR supersedes the old one. Old ADRs are never deleted.

## Index

| Folder | Document | Status |
|---|---|---|
| hackathon | [brief.md](hackathon/brief.md) | Done |
| hackathon | [submission-checklist.md](hackathon/submission-checklist.md) | Living |
| research | [track-analysis.md](research/track-analysis.md) | Done |
| grilling | [round-01.md](grilling/round-01.md) | Answered |
| adr | [0001-company-brain-direction.md](adr/0001-company-brain-direction.md) | Accepted |
| adr | [0002-hybrid-ai-skills-workflow.md](adr/0002-hybrid-ai-skills-workflow.md) | Accepted (partly superseded by 0003) |
| adr | [0003-notion-task-tracking-and-git-conventions.md](adr/0003-notion-task-tracking-and-git-conventions.md) | Accepted |
| adr | [0004-product-scope-and-data.md](adr/0004-product-scope-and-data.md) | Accepted |
| adr | [0005-triage-agent-writes-only-to-sandbox.md](adr/0005-triage-agent-writes-only-to-sandbox.md) | Accepted |
| adr | [0006-graph-freshness.md](adr/0006-graph-freshness.md) | Accepted |
| adr | [0007-graph-query-strategy.md](adr/0007-graph-query-strategy.md) | Accepted |
| adr | [0008-tech-stack.md](adr/0008-tech-stack.md) | Accepted |
| adr | [0009-llm-via-openrouter.md](adr/0009-llm-via-openrouter.md) | Accepted (model choice superseded by 0010) |
| adr | [0010-llm-model-bake-off.md](adr/0010-llm-model-bake-off.md) | Accepted |
| process | [ai-workflow.md](process/ai-workflow.md) | Done |
| process | [ai-usage-disclosure.md](process/ai-usage-disclosure.md) | Living |
| product | SPEC.md | Not started (after grilling) |
| architecture | graph-model.md, system-design.md, cypher-queries.md | Not started |
