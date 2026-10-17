# aevion-web

The Aevion web app (Next.js 16, App Router, Tailwind v4). See the root [README](../../README.md) and [SPEC](../../docs/product/SPEC.md).

```bash
corepack enable && pnpm --dir apps/web install
pnpm --dir apps/web dev        # http://localhost:3000
pnpm --dir apps/web lint && pnpm --dir apps/web typecheck && pnpm --dir apps/web build
pnpm --dir apps/web test:e2e  # Playwright smoke tests, desktop + mobile, against the sample answer
```

The smoke tests build the app and serve it on port 3100 with `AEVION_API_URL` cleared, so they need no API, graph or LLM key. Run `pnpm --dir apps/web exec playwright install chromium` once first.

## Talking to the API

The browser only calls this app's own `POST /api/ask` route, which forwards to the Aevion API:

| Variable | Read at | Meaning |
|---|---|---|
| `AEVION_API_URL` | request time (server only) | Base URL of the FastAPI service, e.g. `http://localhost:8000`. **Unset → a built-in sample answer** recorded from the real FalkorDB graph, so the UI works without the backend. |

Types for API shapes are generated from FastAPI's OpenAPI schema. With the API running:

```bash
pnpm --dir apps/web gen:api    # writes lib/api-schema.ts
```

## Design

Design plan from the Frontend Design skill, checked with UI-UX Pro Max:

- **Colour:** cool paper and blue-black ink; **amber means one thing, a traced evidence path**. Every node type has its own glyph shape, so colour is never the only cue. Text pairs meet WCAG AA in both themes (light amber `#8a560f` is 5.5:1 on paper).
- **Type:** Source Serif 4 for questions and answers, IBM Plex Sans for the interface, IBM Plex Mono only for real code.
- **The memorable element:** the evidence trail beside each answer. Clicking a citation lights its stop on the trail.
- **The graph view:** under each answer, the same evidence path drawn as a graph. The layout is computed once (d3-force, 300 ticks) so nothing moves; selecting a node, by click or keyboard, lights it in the citations and the trail too. **Show Cypher** lists the read-only queries the tools ran.
