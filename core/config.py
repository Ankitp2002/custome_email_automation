import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv(
    override=True
)  # Load environment variables from .env file, allowing overrides


class Settings(BaseSettings):
    PROJECT_NAME: str = "Automated Customer Email Service"
    DEBUG: bool = True

    # smtp settings
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SENDER_EMAIL: str

    GOOGLE_API_KEY: str
    GROQ_API_KEY: str

    class Config:
        env_file = ".env"
