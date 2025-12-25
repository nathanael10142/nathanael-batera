from fastapi import FastAPI, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1.endpoints import (
    auth, admin, users, students, faculties, courses, grades, finances, messages
)
from app.core.firebase_connector import initialize_firebase

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configuration CORS
# En mode DEBUG, on autorise tout pour faciliter le développement mobile/web
if settings.DEBUG:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
elif settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# --- Inclusion des Routeurs API ---
api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(admin.router, prefix="/admin", tags=["Administration"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(students.router, prefix="/students", tags=["Students"])
api_router.include_router(faculties.router, prefix="/faculties", tags=["Faculties & Structure"])
api_router.include_router(courses.router, prefix="/courses", tags=["Courses (UE)"])
api_router.include_router(grades.router, prefix="/grades", tags=["Grades & Deliberation"])
api_router.include_router(finances.router, prefix="/finances", tags=["Finances & Accounting"])
api_router.include_router(messages.router, prefix="/messages", tags=["Messaging"])

app.include_router(api_router, prefix=settings.API_V1_STR)

# --- Initialisation au démarrage ---
@app.on_event("startup")
def startup_event():
    """
    Actions à exécuter au démarrage de l'application.
    """
    initialize_firebase()
