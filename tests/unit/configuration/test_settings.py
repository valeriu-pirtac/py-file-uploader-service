"""Unit tests for AppSettings configuration management."""

from configuration.dependencies import get_settings
from configuration.settings import AppSettings


class TestSettingsDefaults:
    """Test settings load with default values."""

    def test_settings_with_defaults(self, monkeypatch) -> None:
        """Test settings load with default values when required fields provided."""
        for key in [
            "APP_ENV",
            "APP_NAME",
            "LOG_LEVEL",
            "LOG_FORMAT",
            "METRICS_ENABLED",
            "HOST",
            "PORT",
            "WORKERS",
            "REDIS_HOST",
            "REDIS_PORT",
            "REDIS_CONNECT_TIMEOUT",
            "S3_ENDPOINT_URL",
            "S3_ACCESS_KEY_ID",
            "S3_SECRET_ACCESS_KEY",
            "S3_BUCKET_NAME",
            "S3_CONNECT_TIMEOUT",
            "NATS_URL",
            "NATS_CONNECT_TIMEOUT",
        ]:
            monkeypatch.delenv(key, raising=False)
        settings = AppSettings()

        assert settings.app_name == "file-uploader-service"
        assert settings.app_env == "dev"
        assert settings.log_level == "INFO"
        assert settings.log_format == "json"
        assert settings.metrics_enabled
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.workers == 1
        assert settings.redis_host == "localhost"
        assert settings.redis_port == 6379
        assert settings.redis_connect_timeout == 5.0
        assert settings.s3_endpoint_url is None
        assert settings.s3_access_key_id is None
        assert settings.s3_secret_access_key is None
        assert settings.s3_bucket_name == "bronze-file-uploads"
        assert settings.s3_connect_timeout == 5.0
        assert settings.nats_url == "nats://localhost:4222"
        assert settings.nats_connect_timeout == 5


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
