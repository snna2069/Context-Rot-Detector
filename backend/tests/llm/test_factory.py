from __future__ import annotations

from app.config import Settings
from app.services.llm.factory import get_analysis_provider
from app.services.llm.openai_provider import OpenAIAnalysisProvider
from app.services.llm.unavailable import UnavailableAnalysisProvider


def test_factory_returns_unavailable_provider_when_no_api_key() -> None:
    settings = Settings(database_url="sqlite://", llm_api_key=None)
    provider = get_analysis_provider(settings)
    assert isinstance(provider, UnavailableAnalysisProvider)


def test_factory_returns_openai_provider_when_api_key_configured() -> None:
    settings = Settings(database_url="sqlite://", llm_api_key="sk-test")
    provider = get_analysis_provider(settings)
    assert isinstance(provider, OpenAIAnalysisProvider)
