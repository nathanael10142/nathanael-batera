from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List, Union


class Settings(BaseSettings):
    # Basic application info
    APP_NAME: str = "University System"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # API
    API_V1_STR: str = "/api/v1"

    # Security / JWT
    SECRET_KEY: str = "votre_cle_secrete"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # Firebase
    FIREBASE_CREDENTIALS_JSON: Optional[str] = None

    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = ["*"]

    # Redis & Celery (kept for compatibility)
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Pydantic settings
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)


settings = Settings()