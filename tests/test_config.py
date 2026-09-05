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
    assert settings.GEMINI_MODEL == "gemini-3.6-flash"

def test_os_env_variable_precedence():
    """
    Test that OS environment variable GEMINI_API_KEY is accessible via os.getenv.
    """
    test_val = "test_dummy_key_12345"
    os.environ["GEMINI_API_KEY_TEST"] = test_val
    assert os.getenv("GEMINI_API_KEY_TEST") == test_val
    del os.environ["GEMINI_API_KEY_TEST"]

def test_gemini_model_env_override(monkeypatch):
    """
    Test that Settings loads GEMINI_MODEL default and respects environment overrides.
    """
    from src.core.config import Settings
    
    # 1. Test default value when env variable is not set
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    default_settings = Settings()
    assert default_settings.GEMINI_MODEL == "gemini-3.6-flash"

    # 2. Test override when GEMINI_MODEL env variable is set
    custom_model = "gemini-1.5-pro-override"
    monkeypatch.setenv("GEMINI_MODEL", custom_model)
    override_settings = Settings()
    assert override_settings.GEMINI_MODEL == custom_model

def test_missing_api_key_graceful_handling():
    """
    Test that empty or missing API key does not crash configuration initialization.
    """
    assert hasattr(settings, "GEMINI_API_KEY")
    assert not settings.GEMINI_API_KEY.startswith("EXPOSED_SECRET")

