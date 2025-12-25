from pydantic_settings import BaseSettings
from typing import List, Union
import json
from pydantic import field_validator

class Settings(BaseSettings):
    # Variables de l'application
    APP_NAME: str = "University System"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "votre_cle_secrete"
    
    # Base de données
    # Cette variable doit correspondre au nom EXACT dans votre .env
    DATABASE_URL: str = "sqlite+aiosqlite:///./test.db" 
    DATABASE_URL_SYNC: str = ""

    # Variables pour Docker Compose (lues depuis .env)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "university_db"
    
    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = ["*"]

    # Permet de lire les fichiers .env
    model_config = {
        "env_file": ".env",
        "case_sensitive": False, # Très important : ignore la casse (majuscule/minuscule)
        "extra": "ignore"        # Ignore les variables en trop au lieu de planter
    }

settings = Settings()