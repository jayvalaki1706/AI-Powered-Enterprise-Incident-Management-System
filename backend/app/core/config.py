from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Enterprise Incident Management"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    # Redis
    REDIS_URL: str

    # RabbitMQ
    RABBITMQ_URL: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AWS S3
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str

    # Email
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_SERVER: str
    MAIL_PORT: int = 587

    # AI (Ollama - local)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:14b"

    # AI Provider: "ollama" (local/free) or "bedrock" (AWS/paid)
    AI_PROVIDER: str = "ollama"

    # AWS Bedrock (used when AI_PROVIDER=bedrock)
    BEDROCK_MODEL: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    # OpenAI (optional fallback)
    OPENAI_API_KEY: str = ""

    # Frontend
    FRONTEND_URL: str = "http://localhost:5173"

    # CORS (comma-separated origins for production, '*' to allow all)
    CORS_ORIGINS: str = "*"

    # Server
    WORKERS: int = 4

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
