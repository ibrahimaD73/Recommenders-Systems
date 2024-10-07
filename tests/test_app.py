"""
Test module for the BiblioTech 2.0 application.
This module contains essential unit tests for core functionalities of the app.
"""

import os
import sys
from unittest.mock import patch

import pytest
from flask import json

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, books_df, tfidf_matrix, get_book_recommendations, generate_chatbot_response

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
