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
# Copier et rendre le script de démarrage exécutable
COPY ./start.sh /start.sh
RUN chmod +x /start.sh

# Commande pour lancer l'application en production
# Le port sera géré par la variable d'environnement PORT
CMD ["/start.sh"]
