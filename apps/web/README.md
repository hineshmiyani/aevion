# aevion-web

The Aevion web app (Next.js 16, App Router, Tailwind v4). See the root [README](../../README.md) and [SPEC](../../docs/product/SPEC.md).

```bash
corepack enable && pnpm --dir apps/web install
pnpm --dir apps/web dev --port 3001   # http://localhost:3001 (FalkorDB's browser UI uses 3000)
pnpm --dir apps/web lint && pnpm --dir apps/web typecheck && pnpm --dir apps/web build
pnpm --dir apps/web test:e2e  # Playwright smoke tests, desktop + mobile, against the sample answer
```

The smoke tests build the app and serve it on port 3100 with `AEVION_API_URL` cleared, so they need no API, graph or LLM key. Run `pnpm --dir apps/web exec playwright install chromium` once first.

## Talking to the API

The browser only calls this app's own `POST /api/ask` route, which forwards to the Aevion API:

| Variable | Read at | Meaning |
|---|---|---|
| `AEVION_API_URL` | request time (server only) | Base URL of the FastAPI service, e.g. `http://localhost:8000`. **Unset → a built-in sample answer** recorded from the real FalkorDB graph, so the UI works without the backend. |
| `AEVION_PROXY_SECRET` | request time (server only) | Shared with the API's `PROXY_SECRET`. The proxy then forwards each visitor's IP so the API's per-visitor rate limit works behind Vercel; without it every visitor shares one limit. |

Types for API shapes are generated from FastAPI's OpenAPI schema. With the API running:

```bash
pnpm --dir apps/web gen:api    # writes lib/api-schema.ts
```

## Design: the survey sheet (AEV-43)

Direction set with the Frontend Design skill after studying 20 well-crafted products, checked with UI-UX Pro Max, Design Critique and Accessibility Review:

- **The idea:** the org is a map, and an answer's evidence is a **route** across it. The answer's sources are numbered stops; the route follows the graph's own edges between them and draws itself once, leg by leg, when an answer arrives. That is the one orchestrated motion; everything else moves only to show a state change, and nothing moves under `prefers-reduced-motion`.
- **Colour:** chart paper (`#eef1ec`, cool rather than cream) and ink by day, a "night chart" in dark mode; **amber means one thing, the traced evidence path** (route, citations, step markers). The survey grid appears only where the map is drawn. Every node type has its own glyph, so colour is never the only cue.
- **Type:** Newsreader for questions and answers; IBM Plex Sans Condensed for the interface and the map's labels (cartographers use condensed type to fit dense labels); Plex Mono only for real code and keys.
- **Shape:** square corners throughout: the sheet is ruled, not rounded. Radio buttons stay native round, and map glyph shapes encode node type.
- **Ask:** the first screen says what Aevion is, shows live graph stats, and already has a real cached answer's route on the map. Asking streams the agent's real steps (each graph query with its node count and time), then the answer with its speed ("Answered from the graph in 3 ms, cached"). Map, Path and Cypher tabs sit beside every answer.
- **Triage** (`/triage`): the agent's six steps along a route spine, and a map whose route runs from a similar issue, through the code its fix changed, to who knows that code. Acting is only offered for sandbox issues, once per issue.
- **Phones:** the map draws just the route (stops and the nodes linking them); the Path tab lists everything.

Checks: text contrast is 5.4:1 or better and control borders 3.2:1 or better in both themes; `e2e/a11y.spec.ts` runs axe (WCAG 2.2 AA) on both pages, both themes, desktop and mobile.
