from typing import Any, Protocol
from uuid import UUID


class ObjectStorage(Protocol):
    """Abstract protocol for high-performance S3 Multipart Upload streaming."""

    async def initiate_multipart_upload(self, tenant_id: UUID, file_id: UUID) -> str:
        """Initiate S3 Multipart upload.

        Returns:
            The upload ID string.
        """
        ...

    async def upload_part(
        self,
        tenant_id: UUID,
        file_id: UUID,
        upload_id: str,
        part_number: int,
        data: bytes,
    ) -> dict[str, Any]:
        """Upload an individual file part to the S3 bucket.

        Returns:
            A dictionary containing part metadata (e.g. ETag, PartNumber).
        """
        ...

    async def complete_multipart_upload(
        self,
        tenant_id: UUID,
        file_id: UUID,
        upload_id: str,
        parts: list[dict[str, Any]],
    ) -> str:
        """Finalize and assemble the uploaded parts into a single immutable file.

        Returns:
            The final immutable S3 URI referencing the object.
        """
        ...

    async def abort_multipart_upload(self, tenant_id: UUID, file_id: UUID, upload_id: str) -> None:
        """Discard all uploaded parts and terminate the upload session on S3."""
        ...
