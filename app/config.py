from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://localhost:5432/training_platform"

    # Security
    secret_key: str = "change-me-in-production-use-a-long-random-string"

    # Session
    session_expire_days: int = 7

    # SMTP Email
    smtp_host: str = "smtp.example.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "training@vysusgroup.com"
    smtp_use_tls: bool = True

    # App
    base_url: str = "http://localhost:8000"
    environment: str = "development"

    # Password reset
    password_reset_expire_hours: int = 1

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
