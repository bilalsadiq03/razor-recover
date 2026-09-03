from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]

ENV_FILE = PROJECT_ROOT / "backend" / ".env"


class Settings(BaseSettings):
    app_name: str = "RazorRecover"
    environment: str = "development"

    database_url: str
    redis_url: str

    gemini_api_key: str = ""

    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()