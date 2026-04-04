from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configure Pydantic to load environment variables from a ".env" file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_INPUT_TOPIC: str = "input"
    KAFKA_OUTPUT_TOPIC: str = "output"
    KAFKA_ERROR_TOPIC: str = "error"
    KAFKA_DLQ_TOPIC: str = "dead-letter"

    KAFKA_GROUP_ID: str = "kafka-handler-group"

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None

    @field_validator("REDIS_PORT")
    @classmethod
    def validate_redis_port(cls, v: int) -> int:
        if not 1 <= v <= 65535:
            raise ValueError("REDIS_PORT must be between 1 and 65535")
        return v

    @property
    def REDIS_BROKER_URL(self) -> str:
        """Construct the Redis URL for use as a Celery broker."""
        if self.REDIS_PASSWORD:
            return (
                f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
            )
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    CELERY_MAX_RETRIES: int = 3
    CELERY_TASK_TIME_LIMIT: int = 300

    LOG_LEVEL: str = "INFO"


# Instantiate the settings object, loading any overrides from the environment.
settings = Settings()
