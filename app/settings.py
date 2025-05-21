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

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    @property
    def REDIS_BROKER_URL(self) -> str:
        """Construct the Redis URL for use as a Celery broker."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    CELERY_MAX_RETRIES: int = 3


# Instantiate the settings object, loading any overrides from the environment.
settings = Settings()
