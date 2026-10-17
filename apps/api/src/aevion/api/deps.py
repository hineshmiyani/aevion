"""Shared FastAPI dependencies. Tests override `get_db`."""

from functools import lru_cache

from falkordb import FalkorDB

from aevion.config import Settings
from aevion.graph.client import connect


@lru_cache(maxsize=1)
def _db() -> FalkorDB:
    return connect(Settings())


def get_db() -> FalkorDB:
    return _db()
