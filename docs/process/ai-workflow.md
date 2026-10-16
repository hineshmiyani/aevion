# How we work with AI coding assistants

The pipeline and its rationale are in [ADR-0002](../adr/0002-hybrid-ai-skills-workflow.md). This page is the practical how-to.

## Pipeline at a glance

```
grilling ──► domain-modeling ──► spec ──► plan ──► build ──► review ──► ship
 (Matt)         (Matt)          (Addy)   (Addy)   (Addy +    (Addy)    (Addy)
                                                   Matt tdd)
```

| Step | Command in Claude Code | Reads | Writes |
|---|---|---|---|
| 1. Lock decisions | `/grilling` | conversation, `docs/research/` | `docs/grilling/round-NN.md` |
| 2. Domain model | `/mattpocock-skills:domain-modeling` | grilling answers | `GLOSSARY.md`, `docs/adr/`, `docs/architecture/graph-model.md` |
| 3. Spec | `/agent-skills:spec` | ADRs, glossary | `docs/product/SPEC.md` |
| 4. Plan | `/agent-skills:plan` | SPEC.md | `tasks/plan.md`, `tasks/todo.md` |
| 5. Build | `/agent-skills:build` (`/tdd` for Cypher tools) | `tasks/todo.md` | code + tests |
| 6. Review | `/agent-skills:review` | diff | review notes, fixes |
| 7. Ship | `/agent-skills:ship` | everything | deployment + submission |

## Rules for everyone

1. **Pull before you prompt.** The agent reads `CLAUDE.md` and `docs/`; stale docs mean stale code.
2. **Pick one task from `tasks/todo.md`, and put your name on it** before starting, so two people don't build the same thing.
3. **Read what the agent wrote before you commit it.** Rule 12: any of us may be asked to explain any query.
4. **Log significant AI help** in [ai-usage-disclosure.md](ai-usage-disclosure.md) (one line per meaningful session).
5. **New decision? Don't bury it in code.** Add it to the current grilling round, or write an ADR.
