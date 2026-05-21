from typing import Protocol
from uuid import UUID


class EventPublisher(Protocol):
    """Abstract protocol for triggering downstream ingestion processing events."""

    async def publish_file_upload_completed(
        self,
        tenant_id: UUID,
        file_id: UUID,
        s3_uri: str,
        total_size: int,
        checksum: str,
    ) -> None:
        """Publish the FILE_UPLOAD_COMPLETED event to NATS broker."""
        ...
