import os
from unittest import mock
import importlib
from fastapi.testclient import TestClient

def test_cors_local_dev():
    """Test CORS in default local development."""
    with mock.patch("backend.config.IS_CODESPACE", False), \
         mock.patch("backend.config.DEBUG_MODE", False):
        import backend.main
        importlib.reload(backend.main)
        client = TestClient(backend.main.app)
        
        # Test an allowed origin
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

def test_cors_codespaces():
    """Test CORS when running in GitHub Codespaces."""
    with mock.patch("backend.config.IS_CODESPACE", True):
        import backend.main
        importlib.reload(backend.main)
        client = TestClient(backend.main.app)
        
        # In Codespaces, we should allow any origin (or at least the one requesting)
        # for maximum flexibility with dynamic URLs.
        response = client.options(
            "/",
            headers={
                "Origin": "https://random-codespace-url.github.dev",
                "Access-Control-Request-Method": "GET",
            },
        )
        # This will fail currently because the random URL is not in the hardcoded list
        assert response.headers.get("access-control-allow-origin") == "https://random-codespace-url.github.dev"
