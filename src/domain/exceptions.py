"""Domain exception hierarchy.

All domain-specific errors inherit from DomainError. These exceptions
represent business rule violations and are free of framework-specific concepts.
"""


class DomainError(Exception):
    """Base class for all domain exceptions."""


class EntityNotFoundError(DomainError):
    """Raised when a requested domain entity does not exist."""

    def __init__(self, entity: str, identifier: object) -> None:
        super().__init__(f"{entity} with id {identifier!r} was not found.")
        self.entity = entity
        self.identifier = identifier


class ValidationError(DomainError):
    """Raised when a domain invariant or validation rule is violated."""


class DuplicateEntityError(DomainError):
    """Raised when attempting to create an entity that already exists."""

    def __init__(self, entity: str, identifier: object) -> None:
        super().__init__(f"{entity} with id {identifier!r} already exists.")
        self.entity = entity
        self.identifier = identifier


class ChecksumMismatchError(ValidationError):
    """Raised when an uploaded chunk's checksum does not match the provided hash."""

    pass


class MalwareDetectedError(ValidationError):
    """Raised when a virus scanning detects malware in the uploaded stream."""

    pass


class LockAcquisitionError(DomainError):
    """Raised when a distributed lock cannot be acquired for a session."""

    pass
