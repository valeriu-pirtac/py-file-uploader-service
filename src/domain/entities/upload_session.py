from dataclasses import dataclass
from uuid import UUID

from domain.value_objects.upload_status import UploadStatus


@dataclass
class UploadSession:
    """Represents an active chunked upload session."""

    session_id: UUID
    tenant_id: UUID
    file_id: UUID
    total_size: int
    current_offset: int
    checksum: str  # Full file SHA-256 hash
    status: UploadStatus

    def update_offset(self, bytes_uploaded: int) -> None:
        """Advance the current upload offset by the number of bytes uploaded."""
        if bytes_uploaded <= 0:
            raise ValueError("Bytes uploaded must be positive")
        if self.current_offset + bytes_uploaded > self.total_size:
            raise ValueError("Upload exceeds total file size")

        self.current_offset += bytes_uploaded
        if self.current_offset > 0 and self.status == UploadStatus.INITIATED:
            self.status = UploadStatus.UPLOADING

    def complete(self) -> None:
        """Mark the upload session as successfully completed."""
        if self.current_offset != self.total_size:
            raise ValueError(
                f"Cannot complete session: offset ({self.current_offset}) "
                f"does not match total size ({self.total_size})"
            )
        self.status = UploadStatus.COMPLETED

    def abort(self) -> None:
        """Mark the upload session as aborted."""
        self.status = UploadStatus.ABORTED

    def fail(self) -> None:
        """Mark the upload session as failed."""
        self.status = UploadStatus.FAILED
