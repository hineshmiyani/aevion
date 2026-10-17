# ADR-0008: Tech stack: FastAPI (Python) + Next.js (TypeScript)

**Status:** Accepted · **Date:** 2026-10-17 · **Decided by:** the team (Hinesh, Jignesh, Jaydeep, Het) · **Source:** [grilling round 1](../grilling/round-01.md), Q8

## Decision

| Layer | Choice |
|---|---|
| Backend | **Python + FastAPI**: ingestion, agent loop, Cypher tools, MCP server, webhook endpoint |
| Python tooling | **uv** for dependencies and virtual environments |
| Graph client | **falkordb-py** (official client) |
| MCP | Official Python MCP SDK |
| Frontend | **Next.js + TypeScript**: chat UI, evidence-path graph visualisation, triage view |
| Database | FalkorDB (Docker locally; hosting decided in round 2) |

## Why

falkordb-py and the Python MCP SDK are the most mature options, and Python suits ingestion and LLM work. Next.js gives the polished UI judges see first.

## Consequences

- Two languages: the API contract between backend and frontend must be explicit (OpenAPI from FastAPI → generated TS types).
- `uv` must be installed on every machine (not installed on Hinesh's machine as of 2026-10-17).
- Jignesh and Jaydeep can still object in round 2 if their strengths point elsewhere; changing later is costly, so raise it immediately.
