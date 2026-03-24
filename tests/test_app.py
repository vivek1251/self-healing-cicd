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

# --- HOME ---
def test_home_returns_200(client):
    response = client.get('/')
    assert response.status_code == 200

def test_home_returns_message(client):
    data = client.get('/').get_json()
    assert data['message'] == 'Self-Healing CI/CD App'
    assert data['version'] == '1.0'

# --- HEALTH ---
def test_health_returns_healthy(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json()['status'] == 'healthy'

def test_health_force_fail(client):
    os.environ['FORCE_FAIL'] = 'true'
    response = client.get('/health')
    assert response.status_code == 500
    assert response.get_json()['status'] == 'unhealthy'
    del os.environ['FORCE_FAIL']

# --- STATUS ---
def test_status_returns_200(client):
    response = client.get('/status')
    assert response.status_code == 200

def test_status_has_required_fields(client):
    data = client.get('/status').get_json()
    assert data['status'] == 'running'
    assert 'uptime_seconds' in data
    assert 'version' in data
    assert 'timestamp' in data

# --- METRICS ---
def test_metrics_returns_200(client):
    assert client.get('/metrics').status_code == 200

def test_metrics_structure(client):
    data = client.get('/metrics').get_json()
    assert 'deployments' in data
    assert 'auto_healing' in data
    assert 'alerts' in data
    assert data['deployments']['total'] > 0

# --- DEPLOYMENTS ---
def test_get_deployments_returns_list(client):
    data = client.get('/deployments').get_json()
    assert 'deployments' in data
    assert isinstance(data['deployments'], list)

def test_get_single_deployment(client):
    response = client.get('/deployments/1')
    assert response.status_code == 200
    assert response.get_json()['id'] == 1

def test_get_deployment_not_found(client):
    response = client.get('/deployments/999')
    assert response.status_code == 404
    assert 'error' in response.get_json()

def test_create_deployment(client):
    response = client.post('/deployments', json={"branch": "feature/test", "triggered_by": "api"})
    assert response.status_code == 201
    data = response.get_json()
    assert data['branch'] == 'feature/test'
    assert data['status'] == 'success'

# --- ALERTS ---
def test_get_all_alerts(client):
    data = client.get('/alerts').get_json()
    assert 'alerts' in data
    assert data['total'] > 0

def test_get_unresolved_alerts(client):
    data = client.get('/alerts?unresolved=true').get_json()
    for alert in data['alerts']:
        assert alert['resolved'] == False
