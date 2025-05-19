import os

from pydantic_settings import BaseSettings, SettingsConfigDict

env_file_path = ".env" if os.path.exists(".env") else ".env.example"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_file_path,
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
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    CELERY_MAX_RETRIES: int = 3


settings = Settings()
