"""
Application FastAPI principale
"""
from fastapi import FastAPI, Request, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import time
import json
from urllib.parse import urlparse

# ✅ IMPORTS CORRIGÉS (IMPORTANT)
from app.core.config import settings
from app.core.firebase_connector import initialize_firebase
from app.api.v1.endpoints import (
    auth, admin, users, students, faculties, courses, grades, finances, messages, teacher
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application"""
    # Startup
    print("🚀 Démarrage de l'application...")
    print(f"📦 {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"🔧 Debug mode: {settings.DEBUG}")

    # Initialiser la connexion à Firestore
    initialize_firebase()

    yield

    # Shutdown
    print("👋 Arrêt de l'application...")

# Créer l'application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Système de gestion universitaire complet (LMD, admin, finances)",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# --- Configuration CORS (sécurisée) ---
# En production, autorise uniquement le frontend Vercel
DEFAULT_PROD_ORIGINS = [
    "https://nathanael-batera.vercel.app",  # <-- URL frontend Vercel
]

def _normalize_origins(raw):
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        raw = raw.strip()
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        return [raw]
    return []

def _sanitize_origins(origins_list):
    clean = []
    for o in origins_list:
        if not o or o == "*":
            continue
        try:
            parsed = urlparse(o)
            if parsed.scheme in ("http", "https") and parsed.netloc:
                clean.append(o.rstrip('/'))
        except Exception:
            continue
    return list(dict.fromkeys(clean))

if settings.DEBUG:
    origins_to_allow = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8000",
        "http://localhost:52551",
        "http://localhost:8000",
        "http://localhost:56910",
        "http://localhost:49918",
    ]
else:
    raw = getattr(settings, 'BACKEND_CORS_ORIGINS', None)
    origins_to_allow = _sanitize_origins(_normalize_origins(raw))
    if not origins_to_allow:
        origins_to_allow = DEFAULT_PROD_ORIGINS

print(f"🔐 CORS effective allow_origins: {origins_to_allow}")
regex_value = r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$"
print(f"🔐 CORS allow_origin_regex: {regex_value}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins_to_allow,
    allow_origin_regex=regex_value,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body},
    )

# --- Inclusion des Routeurs API ---
api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(admin.router, prefix="/admin", tags=["Administration"])
api_router.include_router(students.router, prefix="/students", tags=["Students"])
api_router.include_router(faculties.router, prefix="/faculties", tags=["Faculties & Structure"])
api_router.include_router(courses.router, prefix="/courses", tags=["Courses (UE)"])
api_router.include_router(grades.router, prefix="/grades", tags=["Grades & Deliberation"])
api_router.include_router(finances.router, prefix="/finances", tags=["Finances & Accounting"])
api_router.include_router(messages.router, prefix="/messages", tags=["Messaging"])
api_router.include_router(teacher.router, tags=["Teachers"])
api_router.include_router(admin.public_router, prefix="", tags=["Public"])

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Monitoring"])
async def health_check():
    """Vérifie que le service est en ligne."""
    return {"status": "healthy"}

@app.get("/")
async def root():
    """Route racine"""
    return {
        "message": f"Bienvenue sur {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/api/docs" if settings.DEBUG else "disabled",
        "api": settings.API_V1_STR
    }

# Pour lancer le serveur en mode développement :
# uvicorn app.main:app --reload --reload-engine watchgod