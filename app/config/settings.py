"""Application configuration and settings."""

import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # Application
    app_name: str = "SkuPhase"
    app_version: str = "2.0.0"
    app_env: str = Field(default="development", pattern="development|staging|production")
    debug: bool = False

    @field_validator("debug", mode="before")
    @classmethod
    def _coerce_debug(cls, v):
        """Tolerate non-boolean DEBUG values from the OS environment.

        Some machines export DEBUG=release globally; pydantic would otherwise
        crash Settings() on startup. Truthy strings enable debug; everything
        else (including 'release'/'prod') is treated as False.
        """
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in {"true", "1", "yes", "on"}
        return bool(v)
    log_level: str = "INFO"
    
    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    
    # Database
    database_url: str = Field(..., description="PostgreSQL connection string")
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Supabase (optional - only needed if using Supabase Storage)
    supabase_url: str = Field(default="https://placeholder.supabase.co", description="Supabase project URL")
    supabase_anon_key: str = Field(default="placeholder", description="Supabase anonymous key")
    supabase_service_key: str = Field(default="placeholder", description="Supabase service role key")
    
    # Authentication
    jwt_secret_key: str = Field(..., min_length=32, description="JWT secret key")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    
    # Google OAuth
    google_client_id: str = Field(default="placeholder.apps.googleusercontent.com", description="Google OAuth client ID")
    google_client_secret: str = Field(default="placeholder", description="Google OAuth client secret")
    google_redirect_uri: str = Field(default="http://localhost:3000/auth/callback")
    
    # LLM Providers
    grok_api_key: str = Field(..., description="Grok API key")
    grok_base_url: str = Field(default="https://api.groq.com/openai/v1", description="Grok API base URL")
    openrouter_api_key: str = Field(default="placeholder", description="OpenRouter API key")
    openai_embedding_api_key: str = Field(default="placeholder", description="OpenAI API key for embeddings")
    
    # File Processing
    max_file_size_mb: int = 25
    pdf_image_extraction_enabled: bool = True
    ocr_enabled: bool = True

    # Background job retries (no external broker)
    background_retry_attempts: int = 3
    background_retry_base_delay_seconds: float = 2.0
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins"
    )
    cors_credentials: bool = True
    cors_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_headers: List[str] = ["*"]
    
    # API
    enable_swagger: bool = True
    api_prefix: str = "/api/v1"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
