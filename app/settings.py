import os

from pydantic_settings import BaseSettings, SettingsConfigDict

env_file_path = ".env" if os.path.exists(".env") else ".env.example"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_file_path,
        env_file_encoding="utf-8",
    )


settings = Settings()
