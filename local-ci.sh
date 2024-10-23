#!/bin/bash

set -e  

# Couleurs pour les messages
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🚀 Démarrage du pipeline CI/CD local${NC}"

# Étape 1: Nettoyage
echo -e "\n${YELLOW}🧹 Nettoyage...${NC}"
make clean || { echo -e "${RED}❌ Échec du nettoyage${NC}"; exit 1; }
echo -e "${GREEN}✅ Nettoyage réussi${NC}"

# Étape 2: Installation des dépendances
echo -e "\n${YELLOW}📦 Installation des dépendances...${NC}"
make install || { echo -e "${RED}❌ Échec de l'installation${NC}"; exit 1; }
echo -e "${GREEN}✅ Installation réussie${NC}"

# Étape 3: Linting et formatage
echo -e "\n${YELLOW}🔍 Vérification du code...${NC}"
make lint || { echo -e "${RED}❌ Échec du linting${NC}"; exit 1; }
echo -e "${GREEN}✅ Code validé${NC}"

# Étape 4: Tests
echo -e "\n${YELLOW}🧪 Exécution des tests...${NC}"
make test || { echo -e "${RED}❌ Échec des tests${NC}"; exit 1; }
echo -e "${GREEN}✅ Tests réussis${NC}"

# Étape 5: Build Docker
echo -e "\n${YELLOW}🐳 Construction de l'image Docker...${NC}"
make build || { echo -e "${RED}❌ Échec du build Docker${NC}"; exit 1; }
echo -e "${GREEN}✅ Build Docker réussi${NC}"

# Étape 6: Test de l'application Docker
echo -e "\n${YELLOW}🚀 Test du conteneur Docker...${NC}"
docker run -d --name bibliotech-test -p 5000:5000 bibliotech
sleep 5  # Attendre que l'application démarre

# Test de l'API
echo -e "\n${YELLOW}🔍 Test de l'API...${NC}"
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000)
if [ $response -eq 200 ]; then
    echo -e "${GREEN}✅ API accessible${NC}"
else
    echo -e "${RED}❌ API inaccessible (Status: $response)${NC}"
    docker logs bibliotech-test
    docker stop bibliotech-test
    docker rm bibliotech-test
    exit 1
fi

# Nettoyage du conteneur de test
docker stop bibliotech-test
docker rm bibliotech-test

echo -e "\n${GREEN}✅ Pipeline CI/CD local terminé avec succès${NC}"