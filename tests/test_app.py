import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    response = client.get('/')
    assert response.status_code == 200

def test_search_route(client):
    response = client.post('/search', json={"query": "python"})
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)

def test_chatbot_route(client):
    response = client.post('/chatbot', json={"message": "Recommend a book"})
    assert response.status_code == 200
    data = response.get_json()
    assert "response" in data
    assert "books" in data
