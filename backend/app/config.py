from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ybs_os"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/ybs_os"
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"
    SECRET_KEY: str = "changeme-in-production-at-least-32-chars"
    ENCRYPTION_KEY: str = "changeme-encryption-key-32-chars!!"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    S3_ENDPOINT: str = ""
    S3_BUCKET: str = "ybs-os-files"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_REGION: str = "us-east-1"
    QB_CLIENT_ID: str = ""
    QB_CLIENT_SECRET: str = ""
    QB_REDIRECT_URI: str = ""
    QB_ENVIRONMENT: str = "sandbox"
    # Plaid (bank account access)
    PLAID_CLIENT_ID: str = ""
    PLAID_SECRET: str = ""
    PLAID_ENV: str = "sandbox"  # sandbox | development | production
    # Google / Gmail
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""
    # Anthropic (AI features)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-opus-4-7"
    # Voyage AI (embeddings for the company brain)
    VOYAGE_API_KEY: str = ""
    VOYAGE_MODEL: str = "voyage-3"
    # GitHub (optional — lets the monitor open draft PRs from approved diagnoses)
    GITHUB_TOKEN: str = ""
    GITHUB_REPO: str = ""
    SWEPT_API_KEY: str = ""
    SWEPT_API_BASE_URL: str = "https://api.swept.com/v1"
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_OPERATOR_CHAT_ID: str = ""
    SENDGRID_API_KEY: str = ""
    NOTIFICATIONS_FROM_EMAIL: str = "noreply@ybs-os.internal"
    HERMES_API_URL: str = "http://hermes:8001"
    OPENCLAW_API_URL: str = "http://openclaw:8002"
    AGENT_CONFIDENCE_AUTO_APPROVE: float = 0.92
    AGENT_CONFIDENCE_NEEDS_REVIEW: float = 0.70
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "http://localhost:3000"
    API_V1_PREFIX: str = "/api/v1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


settings = Settings()
