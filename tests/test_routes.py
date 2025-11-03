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
