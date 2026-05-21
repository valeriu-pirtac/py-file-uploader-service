from typing import Protocol
from uuid import UUID


class MetadataRegistry(Protocol):
    """Abstract protocol for workspace-scoped deduplication registry."""

    async def get_by_checksum(self, tenant_id: UUID, checksum: str) -> str | None:
        """Lookup an existing file within a tenant workspace by its SHA-256 hash.

        Returns:
            The S3 URI reference if found, or None.
        """
        ...

    async def register_file(
        self,
        tenant_id: UUID,
        file_id: UUID,
        s3_uri: str,
        size: int,
        checksum: str,
    ) -> None:
        """Register newly uploaded file metadata for future deduplication queries."""
        ...
