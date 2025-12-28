import os
import importlib
from unittest import mock
import backend.config

def test_codespace_detection():
    """Test that CODESPACES environment variable is correctly detected."""
    with mock.patch.dict(os.environ, {"CODESPACES": "true"}):
        # Reload config to pick up new env var
        importlib.reload(backend.config)
        assert backend.config.IS_CODESPACE is True

def test_debug_mode_detection():
    """Test that DEBUG environment variable is correctly detected."""
    with mock.patch.dict(os.environ, {"DEBUG": "true"}):
        importlib.reload(backend.config)
        assert backend.config.DEBUG_MODE is True

def test_default_detection():
    """Test default values when no env vars are set."""
    with mock.patch.dict(os.environ, {}, clear=True):
        importlib.reload(backend.config)
        assert backend.config.IS_CODESPACE is False
        assert backend.config.DEBUG_MODE is False
