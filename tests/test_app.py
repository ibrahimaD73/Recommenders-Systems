import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app, books_df, tfidf, tfidf_matrix, get_book_recommendations, generate_chatbot_response
from flask import json
from unittest.mock import patch, MagicMock
from sklearn.metrics.pairwise import cosine_similarity

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"BiblioTech 2.0" in response.data

def test_search_route(client):
    response = client.post('/search', json={"query": "python programming"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(isinstance(book, dict) for book in data)

def test_chatbot_route(client):
    response = client.post('/chatbot', json={"message": "Recommend me a science fiction book"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "response" in data
    assert "books" in data
    assert isinstance(data["books"], list)

def test_top_rated_books_route(client):
    response = client.get('/top_rated_books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "labels" in data
    assert "values" in data
    assert len(data["labels"]) == len(data["values"])
    assert len(data["labels"]) == 5  # As we're getting top 5 books

def test_top_read_by_country_route(client):
    response = client.get('/top_read_by_country')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "labels" in data
    assert "values" in data
    assert len(data["labels"]) == len(data["values"])

def test_popular_genres_route(client):
    response = client.get('/popular_genres')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "labels" in data
    assert "values" in data
    assert len(data["labels"]) == len(data["values"])

def test_reading_trends_route(client):
    response = client.get('/reading_trends')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "labels" in data
    assert "values" in data
    assert len(data["labels"]) == len(data["values"])

@patch('app.openai.ChatCompletion.create')
def test_generate_chatbot_response(mock_create):
    mock_create.return_value = {
        "choices": [{"message": {"content": "Mocked chatbot response"}}]
    }
    response = generate_chatbot_response("Test input", [])
    assert "Mocked chatbot response" in response

def test_get_book_recommendations():
    recommendations = get_book_recommendations("python programming")
    assert isinstance(recommendations, list)
    assert len(recommendations) <= 5
    assert all(isinstance(book, dict) for book in recommendations)

@pytest.mark.parametrize("query, min_expected_count, max_expected_count", [
    ("python", 1, 10),
    ("non-existent-book", 0, 5),  # Permettre jusqu'à 5 résultats pour des correspondances partielles
    ("1990", 100, None),  # Permettre un grand nombre de résultats pour une année
])
def test_search_functionality(client, query, min_expected_count, max_expected_count):
    response = client.post('/search', json={"query": query})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) >= min_expected_count
    if max_expected_count is not None:
        assert len(data) <= max_expected_count

def test_data_loading():
    assert not books_df.empty
    assert "ISBN" in books_df.columns
    assert "Book-Title" in books_df.columns
    assert "Book-Author" in books_df.columns

def test_tfidf_matrix():
    assert tfidf_matrix.shape[0] == len(books_df)
    assert tfidf_matrix.shape[1] > 0

def test_error_handling(client):
    response = client.post('/chatbot', json={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "response" in data

def test_search_performance(client):
    import time
    start_time = time.time()
    client.post('/search', json={"query": "python"})
    end_time = time.time()
    assert end_time - start_time < 5 
