# --- Étape 1: Le "Builder" ---
# Cette étape installe toutes les dépendances, y compris les outils de compilation.
FROM python:3.11-slim as builder

WORKDIR /app

# Installe les dépendances système nécessaires pour la compilation
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copie et installe les dépendances Python dans un environnement virtuel
COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt


# --- Étape 2: L'image finale ---
# Cette étape est très légère et ne contient que le nécessaire pour l'exécution.
FROM python:3.11-slim

WORKDIR /app

# Copie l'environnement virtuel avec les paquets déjà installés depuis l'étape "builder"
COPY --from=builder /opt/venv /opt/venv

# Copie les dépendances système d'exécution (pas les outils de compilation)
COPY --from=builder /usr/lib/x86_64-linux-gnu/libmagic.so.1 /usr/lib/x86_64-linux-gnu/

# Copie le code de l'application
COPY . .

# Crée les répertoires nécessaires
RUN mkdir -p /app/uploads /app/logs

EXPOSE 8000

# Active l'environnement virtuel et lance l'application
ENV PATH="/opt/venv/bin:$PATH"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]