from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# Configuration de l'URL de base de données
DATABASE_URL = str(settings.DATABASE_URL)

# Création du moteur asynchrone
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
)

# Utilisation de async_sessionmaker (recommandé pour SQLAlchemy 2.0+)
async_session = async_sessionmaker(
    bind=engine, 
    expire_on_commit=False, 
    class_=AsyncSession
)

# Base pour les modèles
Base = declarative_base()

# Fonction utilitaire pour récupérer une session (Dependency Injection pour FastAPI)
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session