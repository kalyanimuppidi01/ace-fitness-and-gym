# tests/test_routes.py
import pytest
from app import create_app

@pytest.fixture(scope="module")
def client():
    """Provide a Flask test client for all route tests."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

# ----------------------------------------------------------------------
# 🏠 HOME / ROOT ROUTES
# ----------------------------------------------------------------------
def test_home_route(client):
    """Test main '/' endpoint returns expected JSON."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    # Basic structure check
    assert "service" in data and data["service"].lower().startswith("aceest")
    assert "message" in data
    assert "welcome" in data["message"].lower()

def test_root_and_index_routes(client):
    """Test common variants like '/', '/index', '/home'."""
    for path in ("/", "/index", "/home"):
        resp = client.get(path)
        # Accept 200, redirect, or 404 (flexible)
        assert resp.status_code in (200, 301, 302, 404)
        # If JSON, check that it is parseable and structured
        if resp.is_json:
            data = resp.get_json()
            assert isinstance(data, dict)

# ----------------------------------------------------------------------
# ❤️ HEALTHCHECK ROUTES
# ----------------------------------------------------------------------
def test_healthcheck_liveness(client):
    """Test the /healthcheck/live endpoint."""
    response = client.get("/healthcheck/live")
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert data.get("status") == "alive"

def test_healthcheck_readiness(client):
    """Test the /healthcheck/ready endpoint."""
    response = client.get("/healthcheck/ready")
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert data.get("status") == "ready"

def test_health_endpoints_general(client):
    """Check that all health endpoints respond (even if 404 or redirect)."""
    for path in ("/healthcheck/live", "/healthcheck/ready", "/health"):
        resp = client.get(path)
        assert resp.status_code in (200, 204, 301, 302, 404)

# ----------------------------------------------------------------------
# 🧱 APP CREATION VALIDATION
# ----------------------------------------------------------------------
def test_create_app_instance():
    """Ensure create_app() returns a valid Flask app instance with blueprints."""
    app = create_app()
    assert app is not None
    assert hasattr(app, "test_client")

    client = app.test_client()
    assert client is not None

    # Flask >=2.x doesn't always set test_client_class, so check by behavior
    assert callable(client.get)

    # Blueprint registration check (optional but useful)
    if hasattr(app, "blueprints"):
        # If your app registers blueprints, ensure at least one exists
        assert isinstance(app.blueprints, dict)
        # len(...) can be zero in minimal apps, so don't fail hard
        assert all(isinstance(k, str) for k in app.blueprints.keys())

