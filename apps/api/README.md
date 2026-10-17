# aevion (backend)

FastAPI service, ingestion, Cypher tools, agent and MCP server for Aevion. See the root [README](../../README.md) and [SPEC](../../docs/product/SPEC.md).

```bash
docker compose -f infra/docker-compose.yml up -d    # from the repo root
uv sync --project apps/api
uv run --project apps/api uvicorn aevion.api.main:app --reload --port 8000
uv run --project apps/api pytest                     # unit tests
uv run --project apps/api pytest -m integration      # needs FalkorDB running
```

## Use Aevion from Claude Code or Cursor (MCP)

`aevion mcp` serves the five graph tools (`experts_for`, `decision_trail`, `area_history`, `related_work`, `catch_up`) over MCP stdio. With FalkorDB running and the graph ingested:

```bash
claude mcp add aevion -- uv run --project "$(pwd)/apps/api" aevion mcp --org FalkorDB
```

For Cursor or any other MCP client, use the same command:

```json
{ "mcpServers": { "aevion": { "command": "uv", "args": ["run", "--project", "/absolute/path/to/apps/api", "aevion", "mcp", "--org", "FalkorDB"] } } }
```

Every tool result includes `rows`, the `evidence` path (graph nodes and edges with GitHub links) and the `cypher` it ran.
