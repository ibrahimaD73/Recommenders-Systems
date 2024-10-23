PROJECT_ID := $(shell gcloud config get-value project)
IMAGE_NAME := bibliotech
REGION := europe-west1
PORT := 5000
PYTHON_VERSION := 3.9

.PHONY: all install test build run deploy clean setup-gcp

# Commandes principales
all: clean install test build run

install:
	@echo "📦 Installation des dépendances..."
	pip install --no-cache-dir -r requirements.txt
	python -m spacy download en_core_web_sm
	@echo "✅ Installation terminée"

test:
	@echo "🧪 Exécution des tests..."
	pytest tests/ -v --cov=. --cov-report=term-missing
	@echo "✅ Tests terminés"

test-verbose:
	@echo "🧪 Exécution des tests avec détails..."
	pytest tests/ -vv --capture=no

build:
	@echo "🐳 Construction de l'image Docker..."
	docker build -t $(IMAGE_NAME) . --build-arg PORT=$(PORT)
	@echo "✅ Build terminé"

run:
	@echo "🚀 Lancement du conteneur Docker..."
	docker run -p $(PORT):$(PORT) \
		-v $(PWD)/data:/app/data \
		-v $(PWD)/static:/app/static \
		-v $(PWD)/templates:/app/templates \
		$(IMAGE_NAME)

run-local:
	@echo "🚀 Lancement de l'application en local..."
	python app.py

# Commandes de déploiement
deploy:
	@echo "🚀 Déploiement sur Cloud Run..."
	gcloud builds submit --config cloudbuild.yaml

deploy-local:
	@echo "🚀 Déploiement local vers Cloud Run..."
	docker build -t gcr.io/$(PROJECT_ID)/$(IMAGE_NAME) .
	docker push gcr.io/$(PROJECT_ID)/$(IMAGE_NAME)
	gcloud run deploy $(IMAGE_NAME) \
		--image gcr.io/$(PROJECT_ID)/$(IMAGE_NAME) \
		--platform managed \
		--region $(REGION) \
		--port $(PORT) \
		--allow-unauthenticated \
		--memory 2Gi \
		--cpu 2

clean:
	@echo "🧹 Nettoyage des fichiers temporaires..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .eggs/ .coverage htmlcov/ pipeline.log
	@echo "✅ Nettoyage terminé"

setup-gcp:
	@echo "🔧 Configuration de GCP..."
	gcloud auth configure-docker
	gcloud services enable cloudbuild.googleapis.com
	gcloud services enable run.googleapis.com
	gcloud services enable containerregistry.googleapis.com
	gcloud services enable storage.googleapis.com
	@echo "✅ Configuration GCP terminée"

test-docker:
	@echo "🚀 Test du conteneur Docker..."
	@docker run -d --name bibliotech-test -p $(PORT):$(PORT) $(IMAGE_NAME)
	@sleep 5
	@curl -s -o /dev/null -w "%{http_code}" http://localhost:$(PORT) | grep 200 || \
		(docker logs bibliotech-test && docker stop bibliotech-test && docker rm bibliotech-test && exit 1)
	@docker stop bibliotech-test
	@docker rm bibliotech-test
	@echo "✅ Test Docker terminé"

lint:
	@echo "🔍 Vérification du code..."
	pylint *.py
	black --check .
	@echo "✅ Vérification terminée"

format:
	@echo "✨ Formatage du code..."
	black .
	@echo "✅ Formatage terminé"

verify-data:
	@echo "🗃️ Vérification des données..."
	@if [ ! -f data/Books.csv ]; then \
		echo "❌ Fichier Books.csv manquant"; \
		exit 1; \
	fi
	@if [ ! -f data/Book-Ratings.csv ]; then \
		echo "❌ Fichier Book-Ratings.csv manquant"; \
		exit 1; \
	fi
	@if [ ! -f data/Users.csv ]; then \
		echo "❌ Fichier Users.csv manquant"; \
		exit 1; \
	fi
	@echo "✅ Données vérifiées"

backup:
	@echo "💾 Sauvegarde des données..."
	@mkdir -p backups/$(shell date +%Y%m%d)
	@cp data/*.csv backups/$(shell date +%Y%m%d)/
	@cp data/*.pkl backups/$(shell date +%Y%m%d)/ 2>/dev/null || true
	@echo "✅ Sauvegarde terminée dans backups/$(shell date +%Y%m%d)"

check-env:
	@echo "🔍 Vérification de l'environnement..."
	@echo "Python version:"
	@python --version
	@echo "Packages installés:"
	@pip freeze
	@echo "\nDocker version:"
	@docker --version
	@echo "\nGCP Project: $(PROJECT_ID)"
	@echo "Region: $(REGION)"
	@echo "Port: $(PORT)"

logs:
	@echo "📊 Affichage des logs Cloud Build..."
	gcloud builds log-stream

docker-logs:
	@echo "📊 Affichage des logs Docker..."
	docker logs $$(docker ps -q -f name=$(IMAGE_NAME))

docker-shell:
	@echo "🐚 Ouverture d'un shell dans le conteneur..."
	docker exec -it $$(docker ps -q -f name=$(IMAGE_NAME)) /bin/bash

help:
	@echo "🔥 Commandes BiblioTech disponibles:"
	@echo "  Installation et développement:"
	@echo "    make install       - Installe les dépendances"
	@echo "    make run-local    - Lance l'application en local"
	@echo "    make lint         - Vérifie le code"
	@echo "    make format       - Formate le code"
	@echo "  Tests:"
	@echo "    make test         - Lance tous les tests"
	@echo "    make test-verbose - Tests avec plus de détails"
	@echo "  Docker:"
	@echo "    make build        - Construit l'image Docker"
	@echo "    make run          - Lance le conteneur"
	@echo "    make test-docker  - Teste le conteneur"
	@echo "  Déploiement:"
	@echo "    make deploy       - Déploie sur Cloud Run"
	@echo "    make deploy-local - Déploie localement"
	@echo "  Données:"
	@echo "    make verify-data  - Vérifie les données"
	@echo "    make backup       - Sauvegarde les données"
	@echo "  Utilitaires:"
	@echo "    make clean        - Nettoie les fichiers temporaires"
	@echo "    make check-env    - Vérifie l'environnement"
	@echo "    make logs         - Affiche les logs"
	@echo "    make help         - Affiche cette aide"

.DEFAULT_GOAL := help