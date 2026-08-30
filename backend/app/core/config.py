from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RazorRecover"
    environment: str = "development"

    database_url: str
    redis_url: str

    gemini_api_key: str = ""

    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()