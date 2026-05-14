from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_key: str
    max_file_size_mb: int = 25
    log_level: str = "INFO"
    environment: str = "production"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
