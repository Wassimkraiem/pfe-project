from enum import Enum
from typing import Literal

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    LOCAL = "local"
    STAGING = "staging"
    PROD = "prod"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Authentic Rights API"
    ENV: Literal["local", "staging", "prod"] = "local"

    DATABASE_URL: str
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    STRIPE_PRICE_ID_MONTHLY: str = ""
    STRIPE_PRICE_ID_YEARLY: str = ""
    STRIPE_API_VERSION: str = ""
    CLERK_SECRET_KEY: str
    CLERK_JWKS_URL: str
    CLERK_SESSION_TOKEN_EXPIRES_IN_SECONDS: int = 86400  # 24 hours
    FRONTEND_URL: str = "https://authentic-rights-portal.netlify.app"
    STRIPE_CUSTOMER_PORTAL_RETURN_URL: str = (
        "https://authentic-rights-portal.netlify.app/dashboard/subscription"
    )
    # Comma-separated exact origins (required when allow_credentials=True; "*" is not allowed)
    CORS_ORIGINS: str = "https://authentic-rights-portal.netlify.app,http://localhost:3000"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"
    SMS_BASE_URL: str = ""
    SMS_X_API_KEY: str = ""
    SMS_API_KEY: str = ""
    RENEWAL_GRACE_PERIOD_MINUTES: int = 5
    VIDEOS_SEARCH_API_URL: str = "http://localhost:5000"
    VIDEOS_SEARCH_API_KEY: str = "key1"
    RECOMMENDATION_MAX_LIMIT: int = 50
    RECOMMENDATION_DECAY_FACTOR: float = 0.95
    RECOMMENDATION_PERSONALIZED_WEIGHT: float = 0.8
    RECOMMENDATION_UPSTREAM_TIMEOUT_SECONDS: float = 8.0

    @computed_field
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # SMTP Email Configuration
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_REGION: str = ""
    SMTP_USE_TLS: bool = True
    EMAIL_SENDER: str = "noreply@bviral.com"
    EMAIL_SENDER_NAME: str = "BVIRAL Sales Team"
    CUSTOM_QUOTE_TEAM_EMAIL: str = "wassim@smcsoftware.dev"
    PAYMENT_CONFIRMATION_BCC_EMAIL: str = "records@bviral.com"

    STARTUP_STEP_TIMEOUT_SECONDS: float = 30.0
    STARTUP_EXTERNAL_CHECK_TIMEOUT_SECONDS: float = 5.0
    STARTUP_ENABLE_EXTERNAL_CHECKS: bool = False
    STARTUP_ENABLE_DDB_CHECK: bool = False
    STARTUP_DDB_CHECK_TIMEOUT_SECONDS: float = 5.0
    DDB_TABLE_NAME: str = ""
    DDB_REGION: str = ""
    DDB_ENDPOINT_URL: str = ""

    CANTO_AUTH_URL: str = ""
    CANTO_APP_ID: str = ""
    CANTO_APP_SECRET: str = ""
    CANTO_BASIC_PLAN_GROUP_ID: str = "08dae477-413f-48fb-940e-c713d099a030"

    # DB connection pool
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # Sentry (prod only)
    SENTRY_DSN: str = ""

    # Slack Notifications
    SLACK_WEBHOOK_URL: str = ""
    SLACK_WEBHOOK_URL_WHITELISTED: str = ""

    # Thread pool for asyncio.to_thread (JWT validation + Stripe SDK calls)
    # Default Python pool = min(32, cpu_count + 4) = 6 on 2-vCPU ECS task.
    # Each auth'd request needs up to 4 threads (1 JWT + up to 3 Stripe calls).
    # 20 threads handles ~5 concurrent requests per worker before queueing.
    ASYNCIO_THREAD_POOL_SIZE: int = 20

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def is_prod(self) -> bool:
        return self.ENV == Environment.PROD.value

    @property
    def is_staging(self) -> bool:
        return self.ENV == Environment.STAGING.value

    @property
    def is_local(self) -> bool:
        return self.ENV == Environment.LOCAL.value

    @property
    def canto_enabled(self) -> bool:
        """Canto user provisioning is only enabled in prod."""
        return self.is_prod and bool(self.CANTO_APP_ID) and bool(self.CANTO_APP_SECRET)

    @property
    def sentry_enabled(self) -> bool:
        """Sentry is only enabled in prod with a valid DSN."""
        return self.is_prod and bool(self.SENTRY_DSN)

    @property
    def slack_enabled(self) -> bool:
        """Slack notifications are enabled when webhook URL is configured."""
        return bool(self.SLACK_WEBHOOK_URL) and (self.is_prod or self.is_staging)

    @property
    def slack_whitelisted_enabled(self) -> bool:
        """Slack whitelisted channel notifications are enabled when webhook URL is configured."""
        return bool(self.SLACK_WEBHOOK_URL_WHITELISTED) and (self.is_prod )


settings = Settings()
