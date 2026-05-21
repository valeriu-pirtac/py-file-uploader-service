"""Unit tests for domain exception hierarchy."""

import pytest

from domain.exceptions import (
    DomainError,
    DuplicateEntityError,
    EntityNotFoundError,
    ValidationError,
)


@pytest.mark.unit
class TestDomainExceptions:
    """Test domain exception instantiation and messages."""

    def test_entity_not_found_error_message(self) -> None:
        exc = EntityNotFoundError("Item", "abc-123")
        assert "Item" in str(exc)
        assert "abc-123" in str(exc)

    def test_entity_not_found_is_domain_error(self) -> None:
        exc = EntityNotFoundError("Item", 42)
        assert isinstance(exc, DomainError)

    def test_duplicate_entity_error_message(self) -> None:
        exc = DuplicateEntityError("User", "user@example.com")
        assert "User" in str(exc)
        assert "user@example.com" in str(exc)

    def test_validation_error_is_domain_error(self) -> None:
        exc = ValidationError("invalid value")
        assert isinstance(exc, DomainError)

    def test_domain_error_is_exception(self) -> None:
        with pytest.raises(DomainError):
            raise DomainError("something went wrong")
