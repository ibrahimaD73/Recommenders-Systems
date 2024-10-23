import sys
import os
from pathlib import Path

# Ajout du chemin du projet au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app import app

@pytest.fixture
def client():
    """Fixture pour le client de test Flask"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_page(client):
    """Test de la page d'accueil"""
    response = client.get('/')
    assert response.status_code == 200

def test_top_rated_books(client):
    """Test de l'API des livres les mieux notés"""
    response = client.get('/top_rated_books')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert "labels" in data
    assert "values" in data
    assert isinstance(data["labels"], list)
    assert isinstance(data["values"], list)

def test_popular_genres(client):
    """Test de l'API des genres populaires"""
    response = client.get('/popular_genres')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert "labels" in data
    assert "values" in data

def test_reading_trends(client):
    """Test de l'API des tendances de lecture"""
    response = client.get('/reading_trends')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert "labels" in data
    assert "values" in data

def test_search_endpoint(client):
    """Test de l'endpoint de recherche"""
    test_query = {"query": "Python"}
    response = client.post('/search',
                         json=test_query)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)

def test_search_endpoint_empty_query(client):
    """Test de l'endpoint de recherche avec une requête vide"""
    response = client.post('/search',
                         json={"query": ""})
    assert response.status_code == 400 or response.status_code == 200

def test_chatbot_endpoint(client):
    """Test de l'endpoint du chatbot"""
    test_message = {"message": "Recommend a book"}
    response = client.post('/chatbot',
                         json=test_message)
    assert response.status_code == 200
    data = response.get_json()
    assert "response" in data

def test_static_files():
    """Test de l'existence des fichiers statiques essentiels"""
    static_files = [
        'static/styles.css',
        'static/script.js',
        'static/library.png'
    ]
    for file_path in static_files:
        assert os.path.exists(file_path), f"Le fichier {file_path} n'existe pas"

def test_template_exists():
    """Test de l'existence du template index.html"""
    assert os.path.exists('templates/index.html'), "Le fichier index.html n'existe pas"