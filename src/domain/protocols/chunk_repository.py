from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from domain.entities.chunk import Chunk


class ChunkRepository(Protocol):
    """Abstract protocol for temporary chunk segment caching."""

    async def save(self, session_id: UUID, chunk: Chunk) -> None:
        """Cache an individual chunk segment of a session."""
        ...

    async def get(self, session_id: UUID, index: int) -> Chunk | None:
        """Retrieve a specific chunk segment of a session by its index."""
        ...

    async def get_stream(self, session_id: UUID) -> AsyncIterator[bytes]:
        """Stream raw binary chunk contents sequentially from cache."""
        ...

    async def delete_all(self, session_id: UUID) -> None:
        """Purge all temporary chunk keys associated with the session."""
        ...
