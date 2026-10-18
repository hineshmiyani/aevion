"""/healthz reports database status without needing a real FalkorDB."""

from fastapi.testclient import TestClient

from aevion.api.main import app, get_db


class _Connection:
    def __init__(self, healthy: bool) -> None:
        self.healthy = healthy

    def ping(self) -> bool:
        if not self.healthy:
            raise ConnectionError("down")
        return True


class _FakeDB:
    def __init__(self, healthy: bool) -> None:
        self.connection = _Connection(healthy)

    def list_graphs(self) -> list[str]:
        return ["org:FalkorDB"]


def _client(healthy: bool) -> TestClient:
    app.dependency_overrides[get_db] = lambda: _FakeDB(healthy)
    return TestClient(app)


def test_healthz_ok() -> None:
    response = _client(healthy=True).get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"falkordb": "ok", "graphs": ["org:FalkorDB"]}


def test_healthz_reports_database_down() -> None:
    response = _client(healthy=False).get("/healthz")
    assert response.status_code == 503
    assert response.json()["falkordb"] == "unavailable"
