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
from app.core.firebase_connector import initialize_firebase # 👈 CORRECTION: Importer depuis le bon fichier
from app.api.v1.endpoints import (
    auth, admin, users, students, faculties, courses, grades, finances, messages
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
    title=settings.APP_NAME, # Titre de l'API
    version=settings.APP_VERSION, # Version
    description="Système de gestion universitaire complet (LMD, admin, finances)", # Description
    lifespan=lifespan,
    # URLs de la documentation interactive (uniquement en mode DEBUG)
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# --- Configuration CORS (sécurisée) ---
# Defaults: production should allow only the deployed frontend origin(s)
DEFAULT_PROD_ORIGINS = [
    "https://unigom-by-nathanael-batera.onrender.com",
]

def _normalize_origins(raw):
    # Accept list or JSON string or single string
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        raw = raw.strip()
        # try JSON array
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
            # never allow wildcard in production
            continue
        try:
            parsed = urlparse(o)
            if parsed.scheme in ("http", "https") and parsed.netloc:
                clean.append(o.rstrip('/'))
        except Exception:
            continue
    # preserve order and uniqueness
    return list(dict.fromkeys(clean))

if settings.DEBUG:
    # Allow common local dev origins but avoid wildcard in production code path
    origins_to_allow = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]
else:
    raw = getattr(settings, 'BACKEND_CORS_ORIGINS', None)
    origins_to_allow = _sanitize_origins(_normalize_origins(raw))
    if not origins_to_allow:
        origins_to_allow = DEFAULT_PROD_ORIGINS

# Apply middleware with secure defaults
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins_to_allow,
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


# Gestionnaire d'erreurs de validation
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body},
    )

# --- Inclusion des Routeurs API ---
# On crée un routeur principal pour préfixer toutes les routes avec /api/v1
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

# On inclut le routeur principal dans l'application
app.include_router(api_router, prefix=settings.API_V1_STR)

# --- Routes de base (non préfixées par /api/v1) ---
@app.get("/health", tags=["Monitoring"])
async def health_check():
    """Vérifie que le service est en ligne."""
    return {"status": "healthy"}


# Route racine
@app.get("/")
async def root():
    """Route racine"""
    return {
        "message": f"Bienvenue sur {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/api/docs" if settings.DEBUG else "disabled",
        "api": settings.API_V1_STR
    }


# Pour lancer le serveur en mode développement, utilisez la commande suivante
# dans le terminal à la racine du dossier 'backend':
#
# uvicorn app.main:app --reload --reload-engine watchgod
