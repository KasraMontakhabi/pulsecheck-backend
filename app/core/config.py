import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = os.environ.get("DATABASE_URL")

    # Redis
    REDIS_URL: str = os.environ.get("REDIS_URL")

    # Auth
    SECRET_KEY: str = os.environ.get("SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Google OAuth

    # GOOGLE_CLIENT_ID: Optional[str] = None
    # GOOGLE_CLIENT_SECRET: Optional[str] = None

    # Email
    POSTMARK_API_TOKEN: Optional[str] = os.environ.get("POSTMARK_API_TOKEN")
    EMAIL_FROM: str = "noreply@pulsecheck.com"
    EMAIL_DEV_MODE: bool = True

    # App
    APP_NAME: str = "PulseCheck"
    DEBUG: bool = False
    CORS_ORIGINS: list = ["*"]

    # Worker
    MONITOR_CHECK_INTERVAL: int = 30  # seconds
    EMAIL_DEBOUNCE_MINUTES: int = 60

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v):
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    class Config:
        env_file = ".env"

settings = Settings()