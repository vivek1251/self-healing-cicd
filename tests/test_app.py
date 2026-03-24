import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app import app, deployments, alerts

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture(autouse=True)
def clean_env():
    """Ensure FORCE_FAIL is never left set between tests."""
    os.environ.pop('FORCE_FAIL', None)
    yield
    os.environ.pop('FORCE_FAIL', None)


# ─── HOME ────────────────────────────────────────────────────────────────────

def test_home_returns_200(client):
    assert client.get('/').status_code == 200

def test_home_returns_message(client):
    data = client.get('/').get_json()
    assert data['message'] == 'Self-Healing CI/CD App'
    assert data['version'] == '1.0'

def test_home_has_docs_field(client):
    data = client.get('/').get_json()
    assert 'docs' in data


# ─── HEALTH ──────────────────────────────────────────────────────────────────

def test_health_returns_healthy(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json()['status'] == 'healthy'

def test_health_force_fail(client):
    os.environ['FORCE_FAIL'] = 'true'
    response = client.get('/health')
    assert response.status_code == 500
    assert response.get_json()['status'] == 'unhealthy'

def test_health_recovers_after_force_fail(client):
    """Removing FORCE_FAIL should restore healthy response."""
    os.environ['FORCE_FAIL'] = 'true'
    assert client.get('/health').status_code == 500
    del os.environ['FORCE_FAIL']
    assert client.get('/health').status_code == 200

def test_health_returns_json(client):
    response = client.get('/health')
    assert response.content_type == 'application/json'


# ─── STATUS ──────────────────────────────────────────────────────────────────

def test_status_returns_200(client):
    assert client.get('/status').status_code == 200

def test_status_has_required_fields(client):
    data = client.get('/status').get_json()
    assert data['status'] == 'running'
    assert 'uptime_seconds' in data
    assert 'version' in data
    assert 'timestamp' in data

def test_status_uptime_is_non_negative(client):
    data = client.get('/status').get_json()
    assert data['uptime_seconds'] >= 0

def test_status_has_environment_field(client):
    data = client.get('/status').get_json()
    assert 'environment' in data

def test_status_timestamp_is_string(client):
    data = client.get('/status').get_json()
    assert isinstance(data['timestamp'], str)


# ─── VERSION ─────────────────────────────────────────────────────────────────

def test_version_returns_200(client):
    assert client.get('/version').status_code == 200

def test_version_has_required_fields(client):
    data = client.get('/version').get_json()
    assert 'version' in data
    assert 'build' in data
    assert 'author' in data

def test_version_author_is_correct(client):
    data = client.get('/version').get_json()
    assert data['author'] == 'vivek1251'

def test_version_build_is_stable(client):
    data = client.get('/version').get_json()
    assert data['build'] == 'stable'


# ─── METRICS ─────────────────────────────────────────────────────────────────

def test_metrics_returns_200(client):
    assert client.get('/metrics').status_code == 200

def test_metrics_structure(client):
    data = client.get('/metrics').get_json()
    assert 'deployments' in data
    assert 'auto_healing' in data
    assert 'alerts' in data

def test_metrics_deployments_fields(client):
    data = client.get('/metrics').get_json()['deployments']
    assert 'total' in data
    assert 'successful' in data
    assert 'failed' in data
    assert 'success_rate_percent' in data

def test_metrics_success_rate_is_percentage(client):
    rate = client.get('/metrics').get_json()['deployments']['success_rate_percent']
    assert 0 <= rate <= 100

def test_metrics_total_equals_success_plus_failed(client):
    d = client.get('/metrics').get_json()['deployments']
    assert d['total'] == d['successful'] + d['failed']

def test_metrics_auto_healing_fields(client):
    data = client.get('/metrics').get_json()['auto_healing']
    assert 'total_heals' in data
    assert data['max_retries'] == 3
    assert data['check_interval_seconds'] == 10

def test_metrics_alerts_fields(client):
    data = client.get('/metrics').get_json()['alerts']
    assert 'total' in data
    assert 'unresolved' in data


# ─── DEPLOYMENTS ─────────────────────────────────────────────────────────────

def test_get_deployments_returns_list(client):
    data = client.get('/deployments').get_json()
    assert 'deployments' in data
    assert isinstance(data['deployments'], list)

def test_get_deployments_total_matches_list(client):
    data = client.get('/deployments').get_json()
    assert data['total'] == len(data['deployments'])

def test_get_single_deployment(client):
    response = client.get('/deployments/1')
    assert response.status_code == 200
    assert response.get_json()['id'] == 1

def test_get_deployment_not_found(client):
    response = client.get('/deployments/999')
    assert response.status_code == 404
    assert 'error' in response.get_json()

def test_create_deployment_returns_201(client):
    response = client.post('/deployments', json={"branch": "feature/test", "triggered_by": "api"})
    assert response.status_code == 201

def test_create_deployment_fields(client):
    response = client.post('/deployments', json={"branch": "feature/test", "triggered_by": "api"})
    data = response.get_json()
    assert data['branch'] == 'feature/test'
    assert data['status'] == 'success'
    assert data['triggered_by'] == 'api'

def test_create_deployment_defaults_branch_to_main(client):
    response = client.post('/deployments', json={})
    data = response.get_json()
    assert data['branch'] == 'main'

def test_create_deployment_defaults_triggered_by_to_api(client):
    response = client.post('/deployments', json={"branch": "hotfix/bug"})
    data = response.get_json()
    assert data['triggered_by'] == 'api'

def test_create_deployment_increments_id(client):
    before = len(client.get('/deployments').get_json()['deployments'])
    client.post('/deployments', json={"branch": "feat/x"})
    after = len(client.get('/deployments').get_json()['deployments'])
    assert after == before + 1

def test_create_deployment_has_timestamp(client):
    data = client.post('/deployments', json={"branch": "feat/ts"}).get_json()
    assert 'timestamp' in data


# ─── ALERTS ──────────────────────────────────────────────────────────────────

def test_get_all_alerts(client):
    data = client.get('/alerts').get_json()
    assert 'alerts' in data
    assert data['total'] > 0

def test_get_unresolved_alerts(client):
    data = client.get('/alerts?unresolved=true').get_json()
    for alert in data['alerts']:
        assert alert['resolved'] == False

def test_get_all_alerts_includes_resolved(client):
    data = client.get('/alerts').get_json()
    resolved = [a for a in data['alerts'] if a['resolved']]
    assert len(resolved) > 0

def test_alerts_total_matches_list_length(client):
    data = client.get('/alerts').get_json()
    assert data['total'] == len(data['alerts'])

def test_unresolved_total_matches_list(client):
    data = client.get('/alerts?unresolved=true').get_json()
    assert data['total'] == len(data['alerts'])
