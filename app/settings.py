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


settings = Settings()
