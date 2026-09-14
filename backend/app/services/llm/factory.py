"""Selects which `AnalysisProvider` implementation to use.

The only place in the codebase that decides "is a real LLM configured?" --
everywhere else (semantic detectors, the analysis service) just receives
an `AnalysisProvider` and calls it, unaware of which concrete
implementation is behind it.
"""

from __future__ import annotations

from app.config import Settings, get_settings
from app.services.llm.openai_provider import OpenAIAnalysisProvider
from app.services.llm.provider import AnalysisProvider
from app.services.llm.unavailable import UnavailableAnalysisProvider


def get_analysis_provider(settings: Settings | None = None) -> AnalysisProvider:
    settings = settings or get_settings()
    if not settings.llm_api_key:
        return UnavailableAnalysisProvider()
    return OpenAIAnalysisProvider(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )
