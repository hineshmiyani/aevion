"""Aevion HTTP API. Routes are added per module (SPEC section 8)."""

from functools import lru_cache
from typing import Annotated, Any

from falkordb import FalkorDB
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from aevion.config import Settings
from aevion.graph.client import connect

app = FastAPI(title="Aevion API", version="0.1.0")


@lru_cache(maxsize=1)
def _db() -> FalkorDB:
    return connect(Settings())


def get_db() -> FalkorDB:
    return _db()


@app.get("/healthz")
def healthz(db: Annotated[Any, Depends(get_db)]) -> JSONResponse:
    try:
        db.connection.ping()
        graphs = sorted(name for name in db.list_graphs() if not name.startswith("test:"))
    except Exception:
        return JSONResponse(status_code=503, content={"falkordb": "unavailable", "graphs": []})
    return JSONResponse(content={"falkordb": "ok", "graphs": graphs})
