from typing import Protocol
from uuid import UUID

from domain.entities.upload_session import UploadSession


class SessionRepository(Protocol):
    """Abstract protocol for managing UploadSession persistence and locking."""

    async def get(self, session_id: UUID) -> UploadSession | None:
        """Retrieve an upload session by its unique UUID."""
        ...

    async def save(self, session: UploadSession) -> None:
        """Create or update an upload session."""
        ...

    async def delete(self, session_id: UUID) -> None:
        """Purge the upload session state."""
        ...

    async def acquire_lock(self, session_id: UUID, ttl_seconds: int = 10) -> bool:
        """Acquire a session lock for concurrency control.

        Returns:
            True if lock was acquired successfully, False otherwise.
        """
        ...

    async def release_lock(self, session_id: UUID) -> None:
        """Release the session lock."""
        ...
