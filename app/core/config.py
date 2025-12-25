"""
Configuration centrale de l'application
"""
from typing import List, Optional, Any
from pydantic_settings import BaseSettings
from pydantic import validator, PostgresDsn
import os

class Settings(BaseSettings):
    """Configuration de l'application"""

    # Application
    APP_NAME: str = "University Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = "votre_cle_secrete_a_changer_en_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    DATABASE_URL: PostgresDsn
    DATABASE_URL_SYNC: Optional[PostgresDsn] = None

    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: Optional[str]) -> Any:
        if isinstance(v, str):
            # S'assure que le driver asyncpg est utilisé pour les connexions asynchrones
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://")
        return v

    # Redis
    REDIS_URL: str

    # CORS (List[str] pour accepter '*' et URLs réelles)
    BACKEND_CORS_ORIGINS: List[str] = []

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Email
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_FROM: str = "noreply@university.edu"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB

    # LMD Engine Settings
    LMD_CREDITS_PER_YEAR: int = 60
    LMD_PASSING_THRESHOLD: float = 50.0
    LMD_COMPENSATION_ALLOWED: bool = True
    LMD_MAX_DEBT_CREDITS: int = 12

    # Celery (utilise la même URL que Redis par défaut)
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    @validator("CELERY_BROKER_URL", "CELERY_RESULT_BACKEND", pre=True)
    def assemble_celery_url(cls, v: Optional[str], values: dict) -> Any:
        if isinstance(v, str):
            return v
        return values.get("REDIS_URL")

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
        case_sensitive = True
        extra = "ignore"  # Ignore les variables non déclarées dans le .env


# Instance unique pour l'application
settings = Settings()
