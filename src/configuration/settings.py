"""Application configuration management with Pydantic Settings.

This module provides centralized, type-safe configuration management for all
external service dependencies and application settings. Configuration is loaded
from environment variables and .env files with validation at startup.
"""

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown environment variables
    )


class AppSettings(BaseAppSettings):
    """Application configuration with validation.

    All settings are loaded from environment variables or .env file.
    Required fields will raise ValidationError on startup if missing.
    """

    # Application Configuration
    app_name: str = Field(default="file-uploader-service", description="Application name")
    app_env: str = Field(
        default="dev", description="Application environment (e.g. dev, staging, prod)"
    )

    # Observability Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: Literal["json", "console"] = Field(default="json", description="Log format")
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics")

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server bind host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server bind port")
    workers: int = Field(default=1, gt=0, description="Number of worker processes")

    # Redis Configuration
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    redis_connect_timeout: float = Field(
        default=5.0, description="Redis connection timeout in seconds"
    )

    # S3 Storage Configuration
    s3_endpoint_url: str | None = Field(
        default=None, description="Custom S3 endpoint URL (for MinIO/LocalStack)"
    )
    s3_access_key_id: str | None = Field(default=None, description="S3 access key ID")
    s3_secret_access_key: str | None = Field(default=None, description="S3 secret access key")
    s3_bucket_name: str = Field(
        default="bronze-file-uploads", description="S3 bucket name for raw uploads"
    )
    s3_connect_timeout: float = Field(default=5.0, description="S3 connection timeout in seconds")

    # Message Broker Configuration
    nats_url: str = Field(
        default="nats://localhost:4222",
        description="NATS broker connection URL (e.g. nats://localhost:4222)",
    )
    nats_connect_timeout: int = Field(default=5, description="NATS connection timeout in seconds")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid Python logging level.

        Args:
            v: Log level to validate

        Returns:
            Validated log level (uppercase)

        Raises:
            ValueError: If log level is invalid
        """
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v_upper
