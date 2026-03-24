import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# Test 1: home endpoint returns 200
def test_home_returns_200(client):
    response = client.get('/')
    assert response.status_code == 200

# Test 2: home endpoint returns correct message
def test_home_returns_message(client):
    response = client.get('/')
    data = response.get_json()
    assert data['message'] == 'Self-Healing CI/CD App'
    assert data['version'] == '1.0'

# Test 3: health endpoint returns healthy by default
def test_health_returns_healthy(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json()['status'] == 'healthy'

# Test 4: health endpoint returns unhealthy when FORCE_FAIL is set
def test_health_force_fail(client):
    os.environ['FORCE_FAIL'] = 'true'
    response = client.get('/health')
    assert response.status_code == 500
    assert response.get_json()['status'] == 'unhealthy'
    del os.environ['FORCE_FAIL']
