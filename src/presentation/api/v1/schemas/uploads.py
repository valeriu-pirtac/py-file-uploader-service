from uuid import UUID

from pydantic import BaseModel, Field


class InitiateUploadRequest(BaseModel):
    """Schema for initiating a resumable upload session."""

    file_id: UUID = Field(
        ...,
        description="Target File UUID for ingestion mapping.",
    )
    total_size: int = Field(
        ...,
        gt=0,
        le=1024 * 1024 * 1024,  # Up to 1 GB
        description="Total size of the file in bytes.",
    )
    checksum: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA-256 checksum of the entire file.",
    )


class InitiateUploadResponse(BaseModel):
    """Schema returned after a session is successfully initiated."""

    upload_session_id: UUID | None = Field(
        None,
        description="The unique active upload session identifier. None if deduplicated.",
    )
    s3_uri: str | None = Field(
        None,
        description="The immutable S3 URI to the bronze layer if pre-deduplicated.",
    )
    deduplicated: bool = Field(
        ...,
        description="True if the file already existed and was deduplicated.",
    )
