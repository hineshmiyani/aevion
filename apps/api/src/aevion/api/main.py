"""Aevion HTTP API. Routes are added per module (SPEC section 8)."""

import logging
from typing import Annotated, Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from aevion.api.deps import get_db
from aevion.api.routes import ask, tools, triage, webhooks
from aevion.config import Settings

# Uvicorn only configures its own loggers; show ours (webhook triage outcomes and timings) too.
_log = logging.getLogger("aevion")
if not _log.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s - %(message)s"))
    _log.addHandler(_handler)
    _log.setLevel(logging.INFO)

app = FastAPI(title="Aevion API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=Settings().cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(tools.router)
app.include_router(ask.router)
app.include_router(triage.router)
app.include_router(webhooks.router)

__all__ = ["app", "get_db"]


@app.get("/healthz")
def healthz(db: Annotated[Any, Depends(get_db)]) -> JSONResponse:
    try:
        db.connection.ping()
        graphs = sorted(name for name in db.list_graphs() if not name.startswith("test:"))
    except Exception:
        return JSONResponse(status_code=503, content={"falkordb": "unavailable", "graphs": []})
    return JSONResponse(content={"falkordb": "ok", "graphs": graphs})
