# The Aevion API (FastAPI) for Railway (ADR-0012). Build context: the repo root.
FROM python:3.13-slim

# Pinned uv, same version as development.
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1

# Dependencies first, so code changes don't reinstall them.
COPY apps/api/pyproject.toml apps/api/uv.lock apps/api/README.md apps/api/
RUN cd apps/api && uv sync --frozen --no-dev --no-install-project

COPY apps/api/src apps/api/src
COPY config config
RUN cd apps/api && uv sync --frozen --no-dev

# Railway sets PORT. The API keeps its LLM cache and spend ledger on a volume at /data, so
# the budget guard survives redeploys (LLM_DATA_DIR=/data/llm).
CMD ["sh", "-c", "exec uvicorn aevion.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
