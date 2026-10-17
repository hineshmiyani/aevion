# aevion (backend)

FastAPI service, ingestion, Cypher tools, agent and MCP server for Aevion. See the root [README](../../README.md) and [SPEC](../../docs/product/SPEC.md).

```bash
docker compose -f infra/docker-compose.yml up -d    # from the repo root
uv sync --project apps/api
uv run --project apps/api uvicorn aevion.api.main:app --reload --port 8000
uv run --project apps/api pytest                     # unit tests
uv run --project apps/api pytest -m integration      # needs FalkorDB running
```
