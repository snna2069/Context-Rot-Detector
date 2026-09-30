"""Health-endpoint tests.

`/health` is a readiness check, not just a liveness ping: it must fail
when the database is unreachable, otherwise a load balancer would keep
routing traffic to an instance that cannot serve a single request.
"""

from __future__ import annotations

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app


def test_health_endpoint_reports_ok_when_database_reachable(
    client: TestClient,
) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_endpoint_reports_503_when_database_unreachable() -> None:
    class BrokenSession:
        def execute(self, *_args: object, **_kwargs: object) -> None:
            raise OSError("connection refused")

    def override_get_db() -> Generator[Session]:
        yield BrokenSession()  # type: ignore[misc]

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            response = test_client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["database"] == "unreachable"
