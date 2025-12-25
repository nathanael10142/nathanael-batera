# 1. Builder stage
FROM python:3.11-slim as builder
WORKDIR /app
# Copier uniquement le fichier des dépendances pour profiter du cache Docker
COPY requirements.txt .
# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# 2. Final stage
FROM python:3.11-slim
WORKDIR /app
# Copier les dépendances installées depuis le builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
# Copier le code de l'application
COPY . .
EXPOSE 8000

# Commande pour lancer l'application en production
# On enlève --reload qui n'est utile qu'en développement
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
