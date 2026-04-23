from functools import lru_cache

from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="AI Code Review Agent", alias="APP_NAME")
    environment: str = Field(default="dev", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-5-sonnet-20240620", alias="ANTHROPIC_MODEL")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL"
    )

    # Ollama configuration (free local models)
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_primary_model: str = Field(default="codellama", alias="OLLAMA_PRIMARY_MODEL")
    ollama_secondary_model: str = Field(default="llama3", alias="OLLAMA_SECONDARY_MODEL")
    ollama_tertiary_model: str = Field(default="mistral", alias="OLLAMA_TERTIARY_MODEL")
    ollama_timeout: float = Field(default=120.0, alias="OLLAMA_TIMEOUT")
    use_ollama_only: bool = Field(default=False, alias="USE_OLLAMA_ONLY")

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/code_review",
        alias="DATABASE_URL",
    )

    github_webhook_secret: str = Field(default="change-me", alias="GITHUB_WEBHOOK_SECRET")
    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")
    github_api_base_url: str = Field(default="https://api.github.com", alias="GITHUB_API_BASE_URL")
    github_pr_max_files: int = Field(default=25, alias="GITHUB_PR_MAX_FILES")
    github_pr_max_file_chars: int = Field(default=12000, alias="GITHUB_PR_MAX_FILE_CHARS")

    auth_mode: str = Field(default="none", alias="AUTH_MODE")
    auth_api_keys: str = Field(default="", alias="AUTH_API_KEYS")
    jwt_secret: str = Field(default="change-me", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_audience: str | None = Field(default=None, alias="JWT_AUDIENCE")
    jwt_issuer: str | None = Field(default=None, alias="JWT_ISSUER")

    otel_enabled: bool = Field(default=False, alias="OTEL_ENABLED")
    otel_service_name: str = Field(default="ai-code-review-agent", alias="OTEL_SERVICE_NAME")
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None,
        alias="OTEL_EXPORTER_OTLP_ENDPOINT",
    )

    rate_limit_requests: int = Field(default=30, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")

    cache_ttl_seconds: int = Field(default=86400, alias="CACHE_TTL_SECONDS")
    cache_similarity_threshold: float = Field(default=0.92, alias="CACHE_SIMILARITY_THRESHOLD")
    cache_embedding_dimension: int = Field(default=128, alias="CACHE_EMBEDDING_DIMENSION")
    cache_index_max_items: int = Field(default=1500, alias="CACHE_INDEX_MAX_ITEMS")

    circuit_breaker_failure_threshold: int = Field(
        default=3, alias="CIRCUIT_BREAKER_FAILURE_THRESHOLD"
    )
    circuit_breaker_recovery_seconds: int = Field(
        default=30,
        alias="CIRCUIT_BREAKER_RECOVERY_SECONDS",
    )

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        env = (self.environment or "").strip().lower()
        if env not in {"prod", "production"}:
            return self

        if (self.github_webhook_secret or "").strip() in {"", "change-me"}:
            raise ValueError("GITHUB_WEBHOOK_SECRET must be set in production.")
        if (self.jwt_secret or "").strip() in {"", "change-me"}:
            raise ValueError("JWT_SECRET must be set in production.")

        mode = (self.auth_mode or "").strip().lower()
        if mode in {"api_key", "both"} and not (self.auth_api_keys or "").strip():
            raise ValueError("AUTH_API_KEYS must be set when AUTH_MODE requires api_key in production.")

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
