from app.config import Settings


def test_settings_use_safe_local_defaults() -> None:
    settings = Settings()

    assert settings.environment == "development"
    assert settings.database_url.startswith("postgresql+psycopg2://")
    assert settings.cors_origins == ["http://localhost:3000"]
