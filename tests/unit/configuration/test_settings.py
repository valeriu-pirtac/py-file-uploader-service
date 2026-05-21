"""Unit tests for AppSettings configuration management."""

from configuration.dependencies import get_settings
from configuration.settings import AppSettings


class TestSettingsDefaults:
    """Test settings load with default values."""

    def test_settings_with_defaults(self) -> None:
        """Test settings load with default values when required fields provided."""
        settings = AppSettings()

        assert settings.app_name == "python-project-template"
        assert settings.app_env == "dev"
        assert settings.log_level == "INFO"
        assert settings.log_format == "json"
        assert settings.metrics_enabled
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.workers == 1


class TestSingletonPattern:
    """Test that get_settings returns singleton instance."""

    def test_get_settings_returns_same_instance(self) -> None:
        """Test get_settings returns the same instance on multiple calls."""

        # Clear cache to ensure clean test
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_singleton_persists_across_calls(self) -> None:
        """Test singleton pattern maintains same object identity."""

        # Clear cache to ensure clean test
        get_settings.cache_clear()

        first_call = get_settings()
        second_call = get_settings()
        third_call = get_settings()

        assert first_call is second_call is third_call
