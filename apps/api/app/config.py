from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(
        default="development",
        validation_alias=AliasChoices("APP_ENV", "ENVIRONMENT"),
    )
    api_key: str = "dev-api-key"
    slack_webhook_url: str | None = None
    slack_alert_channel: str | None = None
    postgres_db: str = "basket_monitor"
    postgres_user: str = "basket"
    postgres_password: str = "basket"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_ttl_live_seconds: int = 300
    redis_ttl_historical_seconds: int = 86400

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
