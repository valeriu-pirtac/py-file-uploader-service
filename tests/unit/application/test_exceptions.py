"""Unit tests for application exception hierarchy."""

import pytest

from application.exceptions import ApplicationError, DependencyError, UseCaseError


@pytest.mark.unit
class TestApplicationExceptions:
    """Test application exception instantiation and hierarchy."""

    def test_use_case_error_is_application_error(self) -> None:
        exc = UseCaseError("use case failed")
        assert isinstance(exc, ApplicationError)

    def test_dependency_error_is_application_error(self) -> None:
        exc = DependencyError("service unavailable")
        assert isinstance(exc, ApplicationError)

    def test_application_error_is_exception(self) -> None:
        with pytest.raises(ApplicationError):
            raise ApplicationError("something went wrong")
