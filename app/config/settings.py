"""Application configuration via pydantic-settings.

All fields map to environment variables (case-insensitive).
List-valued fields (CORS_*) accept either JSON arrays or
comma-separated strings.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_list(value):
    """Accept JSON lists or comma-separated strings for list settings."""
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.startswith("["):
            return value  # let pydantic parse JSON
        return [item.strip() for item in cleaned.split(",") if item.strip()]
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "SkuPhase"
    app_version: str = "2.0.0"
    app_env: str = Field(
        default="development",
        description="development, staging, release, production",
    )
    debug: bool = True
    log_level: str = "INFO"

    @field_validator("app_env", mode="before")
    @classmethod
    def _normalize_app_env(cls, v):
        """Tolerate machine-wide DEBUG-style values like 'release'."""
        if isinstance(v, str):
            return v.strip().lower()
        return v

    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8000

    # Database (PostgreSQL)
    database_url: str

    # Connection pool (long-lived VPS/container deployments)
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Authentication
    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # Email delivery (provider switchable; see app/services/mailer.py)
    mail_provider: str = "smtp"  # smtp | resend
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    resend_api_key: str = ""
    mail_from: str = ""  # falls back to smtp_user for SMTP
    app_base_url: str = "http://localhost:3000"

    # LLM providers ("Groq" primary, OpenRouter fallback)
    groq_api_key: str
    groq_base_url: str = "https://api.groq.com/openai/v1"
    openrouter_api_key: str = ""

    # Background retries (Postgres-backed jobs)
    background_retry_attempts: int = 3
    background_retry_base_delay_seconds: float = 2.0

    # In-app worker concurrency (jobs processed in parallel per instance)
    worker_concurrency: int = 3
    # Hard timeout for a single LLM provider call (seconds). Must stay well
    # below the stale-running job reap window in job_queue.py.
    llm_timeout_seconds: int = 120

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    cors_methods: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    cors_headers: list[str] = ["*"]
    cors_credentials: bool = True

    @field_validator("cors_origins", "cors_methods", "cors_headers", mode="before")
    @classmethod
    def _coerce_cors_lists(cls, v):
        return _split_list(v)

    # API docs
    enable_swagger: bool = True

    @field_validator("debug", mode="before")
    @classmethod
    def _tolerant_debug(cls, v):
        """Accept machine-wide values like DEBUG=release without crashing."""
        if isinstance(v, str):
            lowered = v.strip().lower()
            if lowered in {"true", "1", "yes", "on"}:
                return True
            if lowered in {"false", "0", "no", "off", "release", "production"}:
                return False
        return v


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings
