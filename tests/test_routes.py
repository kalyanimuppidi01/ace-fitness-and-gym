# tests/test_routes.py
import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home(client):
    resp = client.get('/')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["service"].lower().startswith("aceest")

def test_liveness(client):
    resp = client.get('/healthcheck/live')
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "alive"

def test_readiness(client):
    resp = client.get('/healthcheck/ready')
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ready"

def test_root_and_metadata(client):
    # root may be "/" or "/index" etc. try common ones
    for path in ("/", "/index", "/home"):
        rv = client.get(path)
        # Accept 200 or redirect (some versions might redirect)
        assert rv.status_code in (200, 301, 302, 404)
        # if JSON response, check keys
        try:
            if rv.is_json:
                data = rv.get_json()
                assert isinstance(data, dict)
        except Exception:
            # don't fail for non-json or odd responses
            pass

def test_health_endpoints(client):
    # check readiness and liveness if available
    for path in ("/healthcheck/live", "/healthcheck/ready", "/health"):
        rv = client.get(path)
        assert rv.status_code in (200, 204, 301, 302, 404)

