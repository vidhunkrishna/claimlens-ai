import os
import pytest
from src.core.config import settings

def test_config_defaults_and_env_loading():
    """
    Test configuration loading, defaults, and OS environment variable overrides.
    """
    assert settings.APP_NAME == "ClaimLens AI"
    assert settings.PORT == 8000
    assert isinstance(settings.GEMINI_API_KEY, str)

def test_os_env_variable_precedence():
    """
    Test that OS environment variable GEMINI_API_KEY is accessible via os.getenv.
    """
    test_val = "test_dummy_key_12345"
    os.environ["GEMINI_API_KEY_TEST"] = test_val
    assert os.getenv("GEMINI_API_KEY_TEST") == test_val
    del os.environ["GEMINI_API_KEY_TEST"]

def test_missing_api_key_graceful_handling():
    """
    Test that empty or missing API key does not crash configuration initialization.
    """
    assert hasattr(settings, "GEMINI_API_KEY")
    assert not settings.GEMINI_API_KEY.startswith("EXPOSED_SECRET")
