"""Application exception hierarchy.

Application-layer exceptions represent failures in use-case orchestration
rather than domain rule violations.
"""

from domain.exceptions import DomainError


class ApplicationError(Exception):
    """Base class for all application-layer exceptions."""


class UseCaseError(ApplicationError):
    """Raised when a use case cannot complete due to an unexpected condition."""


class DependencyError(ApplicationError):
    """Raised when a required infrastructure dependency is unavailable."""


__all__ = [
    "ApplicationError",
    "DependencyError",
    "DomainError",
    "UseCaseError",
]
