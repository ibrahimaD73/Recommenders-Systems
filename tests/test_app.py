import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    """Test the index route of the application."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"BiblioTech 2.0" in response.data
