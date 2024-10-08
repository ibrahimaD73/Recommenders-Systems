# Utiliser une image Python
FROM python:3.9-slim

# Installer les dépendances système
RUN apt-get update && apt-get install -y build-essential libssl-dev libffi-dev python3-dev

# Créer un répertoire de travail
WORKDIR /app

# Copier les fichiers dans le conteneur
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste des fichiers de l'application
COPY . .

# Exposer le port 8080 pour Flask
EXPOSE 8080

# Commande pour démarrer l'application Flask
CMD ["python", "app.py"]

