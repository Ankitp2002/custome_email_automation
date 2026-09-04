from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv(override=True)


class Settings(BaseSettings):
    PROJECT_NAME: str = "Automated Customer Email Service"
    DEBUG: bool = True

    # smtp settings
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SENDER_EMAIL: str
    ATTACHMENT_PATH: str

    GOOGLE_API_KEY: str
    GROQ_API_KEY: str

    SEARCH_API_URL: str
    SEARCH_API_KEY: str

    class Config:
        env_file = ".env"
        allow_override = True
        extra = "allow"
