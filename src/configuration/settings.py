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
    app_name: str = Field(default="python-project-template", description="Application name")
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
