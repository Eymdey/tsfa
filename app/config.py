"""Application configuration via Pydantic-settings.

All settings are loaded from environment variables or .env file.
Never hardcode configuration values — always use this module.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_version: str = "v1"
    debug: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 900

    # Modal (Phase 2)
    modal_token_id: str = ""
    modal_token_secret: str = ""
    modal_app_name: str = "tsfa-inference"

    # RapidAPI
    rapidapi_proxy_secret: str = ""

    # MLflow
    mlflow_tracking_uri: str = "http://localhost:5000"

    # Sentry
    sentry_dsn: str = ""

    # Plans (credits/month)
    plan_free_credits: int = 500
    plan_basic_credits: int = 10000
    plan_pro_credits: int = 50000
    plan_ultra_credits: int = 200000


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings: Settings = get_settings()
