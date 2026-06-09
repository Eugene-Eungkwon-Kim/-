from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./data/npl_avm.db"
    ANTHROPIC_API_KEY: str = ""
    KOREA_API_KEY: str = ""
    KAKAO_REST_API_KEY: str = ""

    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
