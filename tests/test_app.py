"""
Test module for the BiblioTech 2.0 application.
This module contains unit tests for various routes and functions of the app.
"""

import os
import sys
import time
from unittest.mock import patch

import pytest
from flask import json

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import (
    app, books_df, tfidf_matrix, get_book_recommendations, generate_chatbot_response
)

@pytest.fixture(scope="module")
def client():
    """Provides a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as test_client:
        yield test_client

def test_index_route(client):
    """Test the index route of the application."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"BiblioTech 2.0" in response.data

def test_search_route(client):
    """Test the search route of the application."""
    response = client.post('/search', json={"query": "python programming"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(isinstance(book, dict) for book in data)

def test_chatbot_route(client):
    """Test the chatbot route of the application."""
    response = client.post('/chatbot', json={"message": "Recommend a science fiction book"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "response" in data
    assert "books" in data
    assert isinstance(data["books"], list)

def test_top_rated_books_route(client):
    """Test the top rated books route of the application."""
    response = client.get('/top_rated_books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "labels" in data
    assert "values" in data
    assert len(data["labels"]) == len(data["values"])
    assert len(data["labels"]) == 5  # As we're getting top 5 books

def test_top_read_by_country_route(client):
    """Test the top read by country route of the application."""
    response = client.get('/top_read_by_country')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "labels" in data
    assert "values" in data
    assert len(data["labels"]) == len(data["values"])

def test_popular_genres_route(client):
    """Test the popular genres route of the application."""
    response = client.get('/popular_genres')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "labels" in data
    assert "values" in data
    assert len(data["labels"]) == len(data["values"])

def test_reading_trends_route(client):
    """Test the reading trends route of the application."""
    response = client.get('/reading_trends')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "labels" in data
    assert "values" in data
    assert len(data["labels"]) == len(data["values"])

@patch('app.openai.ChatCompletion.create')
def test_generate_chatbot_response(mock_create):
    """Test the generate_chatbot_response function."""
    mock_create.return_value = {
        "choices": [{"message": {"content": "Mocked chatbot response"}}]
    }
    response = generate_chatbot_response("Test input", [])
    assert "Mocked chatbot response" in response

def test_get_book_recommendations():
    """Test the get_book_recommendations function."""
    recommendations = get_book_recommendations("python programming")
    assert isinstance(recommendations, list)
    assert len(recommendations) <= 5
    assert all(isinstance(book, dict) for book in recommendations)

@pytest.mark.parametrize("query, min_expected_count, max_expected_count", [
    ("python", 1, 10),
    ("non-existent-book", 0, 5),  # Allow up to 5 results for partial matches
    ("1990", 100, None),  # Allow a large number of results for a year
])
def test_search_functionality(client, query, min_expected_count, max_expected_count):
    """Test the search functionality with various queries."""
    response = client.post('/search', json={"query": query})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) >= min_expected_count
    if max_expected_count is not None:
        assert len(data) <= max_expected_count

def test_data_loading():
    """Test the data loading process."""
    assert not books_df.empty
    assert "ISBN" in books_df.columns
    assert "Book-Title" in books_df.columns
    assert "Book-Author" in books_df.columns

def test_tfidf_matrix():
    """Test the TF-IDF matrix creation."""
    assert tfidf_matrix.shape[0] == len(books_df)
    assert tfidf_matrix.shape[1] > 0

def test_error_handling(client):
    """Test the error handling of the application."""
    response = client.post('/chatbot', json={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "response" in data

def test_search_performance(client):
    """Test the performance of the search functionality."""
    start_time = time.time()
    client.post('/search', json={"query": "python"})
    end_time = time.time()
    assert end_time - start_time < 5

