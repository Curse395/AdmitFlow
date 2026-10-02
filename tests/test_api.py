from fastapi.testclient import TestClient

from backend.admitflow.server import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_analytics_requires_bearer_token():
    response = client.get('/api/dashboard')
    assert response.status_code == 401


def test_cors_allows_local_frontend_without_credentials():
    response = client.options(
        '/api/dashboard',
        headers={
            'Origin': 'http://localhost:5173',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'authorization',
        },
    )
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'
    assert 'access-control-allow-credentials' not in response.headers


def test_login_and_dashboard():
    login_response = client.post('/auth/login', json={'email': 'admin@admitflow.local', 'password': 'admin123'})
    assert login_response.status_code == 200
    token = login_response.json()['token']
    headers = {'Authorization': f'Bearer {token}'}

    dashboard = client.get('/api/dashboard', headers=headers)
    assert dashboard.status_code == 200
    assert 'applications' in dashboard.json()

    funnel = client.get('/api/funnel', headers=headers)
    assert funnel.status_code == 200
    assert funnel.json()['baseline_applications'] == dashboard.json()['applications']
    volumes = [row['volume'] for row in funnel.json()['stage_summary']]
    assert volumes == sorted(volumes, reverse=True)

    forecast = client.get('/api/forecast', headers=headers)
    assert forecast.status_code == 200
    assert set(forecast.json()['horizons']) == {'H1', 'H2', 'H4', 'H6'}

    cohorts = client.get('/api/cohorts', headers=headers)
    assert cohorts.status_code == 200
    assert {'cycle', 'programme', 'region', 'selectivity'} <= cohorts.json().keys()
    for route in ('/api/programmes', '/api/attribution', '/api/cycle'):
        response = client.get(route, headers=headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    scenario = client.post('/api/scenarios/run', json={'application_volume': 5200}, headers=headers)
    assert scenario.status_code == 200
    assert 'baseline' in scenario.json()

    auth_check = client.get('/api/audit', headers=headers)
    assert auth_check.status_code == 200
    assert isinstance(auth_check.json(), list)

    logout = client.post('/auth/logout', params={'token': token})
    assert logout.status_code == 200


def test_invalid_login_is_rejected():
    response = client.post('/auth/login', json={'email': 'x', 'password': 'y'})
    assert response.status_code == 401
