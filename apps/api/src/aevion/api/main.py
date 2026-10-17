"""Aevion HTTP API. Routes are added per module (SPEC section 8)."""

from typing import Annotated, Any

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from aevion.api.deps import get_db
from aevion.api.routes import ask, tools, triage

app = FastAPI(title="Aevion API", version="0.1.0")
app.include_router(tools.router)
app.include_router(ask.router)
app.include_router(triage.router)

__all__ = ["app", "get_db"]


@app.get("/healthz")
def healthz(db: Annotated[Any, Depends(get_db)]) -> JSONResponse:
    try:
        db.connection.ping()
        graphs = sorted(name for name in db.list_graphs() if not name.startswith("test:"))
    except Exception:
        return JSONResponse(status_code=503, content={"falkordb": "unavailable", "graphs": []})
    return JSONResponse(content={"falkordb": "ok", "graphs": graphs})
