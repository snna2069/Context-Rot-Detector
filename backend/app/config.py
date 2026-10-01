from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Context Rot Detector API"
    app_version: str = "0.1.0"
    environment: str = "development"
    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/context_rot",
        validation_alias="DATABASE_URL",
    )
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        validation_alias="CORS_ORIGINS",
    )
    api_key: str | None = Field(default=None, validation_alias="API_KEY")
    auth_enabled: bool | None = Field(default=None, validation_alias="AUTH_ENABLED")
    analysis_rate_limit_per_minute: int = Field(
        default=60, validation_alias="ANALYSIS_RATE_LIMIT_PER_MINUTE"
    )

    # Optional LLM provider for semantic analysis (Phase 5). When unset,
    # `app.services.llm.factory.get_analysis_provider` falls back to the
    # safe `UnavailableAnalysisProvider`, so semantic analysis degrades to
    # "no signal" rather than failing -- an LLM key is never required for
    # the deterministic detectors or for running the app at all.
    llm_api_key: str | None = Field(default=None, validation_alias="LLM_API_KEY")
    llm_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias="LLM_BASE_URL",
    )
    llm_model: str = Field(default="gpt-4o-mini", validation_alias="LLM_MODEL")
    llm_timeout_seconds: float = Field(
        default=20.0, validation_alias="LLM_TIMEOUT_SECONDS"
    )
    llm_max_retries: int = Field(default=2, validation_alias="LLM_MAX_RETRIES")
    llm_retry_backoff_seconds: float = Field(
        default=0.25, validation_alias="LLM_RETRY_BACKOFF_SECONDS"
    )
    llm_max_calls_per_analysis: int = Field(
        default=24, validation_alias="LLM_MAX_CALLS_PER_ANALYSIS"
    )

    # Context-health scoring (Phase 6). These are deliberately configurable
    # rather than hard-coded in `app.analysis.health`, so the relative
    # importance of each dimension (or how harshly a single signal is
    # penalized) can be tuned per deployment/environment without a code
    # change or redeploy of the detectors themselves. See
    # `app.analysis.health.HealthScoreWeights` for how these are consumed.
    health_penalty_per_signal: float = Field(
        default=0.15, validation_alias="HEALTH_PENALTY_PER_SIGNAL"
    )
    health_weight_consistency: float = Field(
        default=1.0, validation_alias="HEALTH_WEIGHT_CONSISTENCY"
    )
    health_weight_instruction_adherence: float = Field(
        default=1.0, validation_alias="HEALTH_WEIGHT_INSTRUCTION_ADHERENCE"
    )
    health_weight_information_retention: float = Field(
        default=1.0, validation_alias="HEALTH_WEIGHT_INFORMATION_RETENTION"
    )
    health_weight_relevance: float = Field(
        default=1.0, validation_alias="HEALTH_WEIGHT_RELEVANCE"
    )
    health_weight_tool_utilization: float = Field(
        default=1.0, validation_alias="HEALTH_WEIGHT_TOOL_UTILIZATION"
    )
    health_weight_hallucination_risk: float = Field(
        default=1.0, validation_alias="HEALTH_WEIGHT_HALLUCINATION_RISK"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def require_api_key(self) -> bool:
        """Require API-key auth unless development explicitly opts out."""
        if self.auth_enabled is not None:
            return self.auth_enabled
        return self.environment.lower() != "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
