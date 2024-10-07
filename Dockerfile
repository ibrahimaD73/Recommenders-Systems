# Utiliser une image Python officielle comme image de base
FROM python:3.9-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier les fichiers de dépendances et installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code de l'application dans le conteneur
COPY . .

# Définir les variables d'environnement
ENV GCP_PROJECT_ID=sytem-recommder
ENV GCP_BUCKET_NAME=system_recommendation

# Exposer le port sur lequel l'application s'exécutera
EXPOSE 8080

# Commande pour exécuter l'application
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
