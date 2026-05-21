from enum import StrEnum


class UploadStatus(StrEnum):
    """Lifecycle states of a chunked upload session."""

    INITIATED = "INITIATED"
    UPLOADING = "UPLOADING"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    FAILED = "FAILED"
