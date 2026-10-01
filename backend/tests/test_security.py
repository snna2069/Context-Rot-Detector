"""Phase 4 security-boundary tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

import app.auth as auth
import app.main as main


def test_development_mode_allows_requests_without_a_key(client: TestClient) -> None:
    response = client.get("/sessions")

    assert response.status_code == 200


def test_enabled_auth_rejects_missing_key(client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    class Settings:
        require_api_key = True
        api_key = "internal-secret"

    monkeypatch.setattr(auth, "get_settings", lambda: Settings())

    response = client.get("/sessions")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "ApiKey"


def test_enabled_auth_rejects_wrong_key(client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    class Settings:
        require_api_key = True
        api_key = "internal-secret"

    monkeypatch.setattr(auth, "get_settings", lambda: Settings())

    response = client.get("/sessions", headers={"X-API-Key": "wrong"})

    assert response.status_code == 401


def test_enabled_auth_accepts_configured_key(client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    class Settings:
        require_api_key = True
        api_key = "internal-secret"

    monkeypatch.setattr(auth, "get_settings", lambda: Settings())

    response = client.get("/sessions", headers={"X-API-Key": "internal-secret"})

    assert response.status_code == 200


def test_enabled_auth_fails_closed_when_key_is_missing(
    client: TestClient, monkeypatch
) -> None:  # noqa: ANN001
    class Settings:
        require_api_key = True
        api_key = None

    monkeypatch.setattr(auth, "get_settings", lambda: Settings())

    response = client.get("/sessions")

    assert response.status_code == 503


def test_analysis_rate_limit_returns_429_after_configured_budget(
    client: TestClient, monkeypatch
) -> None:  # noqa: ANN001
    main._analysis_requests.clear()
    monkeypatch.setattr(main.settings, "analysis_rate_limit_per_minute", 1)

    first = client.post("/sessions/does-not-exist/analyze")
    second = client.post("/sessions/does-not-exist/analyze")

    assert first.status_code == 404
    assert second.status_code == 429
    assert second.headers["retry-after"] == "60"
    main._analysis_requests.clear()
