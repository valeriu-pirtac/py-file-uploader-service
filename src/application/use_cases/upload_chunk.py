import hashlib
from uuid import UUID

import structlog

from domain.entities.chunk import Chunk
from domain.entities.upload_session import UploadSession
from domain.exceptions import (
    ChecksumMismatchError,
    EntityNotFoundError,
    LockAcquisitionError,
    ValidationError,
)
from domain.protocols.chunk_repository import ChunkRepository
from domain.protocols.session_repository import SessionRepository
from domain.value_objects.upload_status import UploadStatus


log = structlog.get_logger(__name__)


class UploadChunkUseCase:
    """Use case to handle uploading an individual file chunk segment."""

    def __init__(
        self,
        session_repo: SessionRepository,
        chunk_repo: ChunkRepository,
    ) -> None:
        self.session_repo = session_repo
        self.chunk_repo = chunk_repo

    async def execute(
        self,
        session_id: UUID,
        chunk_index: int,
        checksum: str,
        data: bytes,
    ) -> UploadSession:
        """Process and validate an uploaded chunk segment.

        Args:
            session_id: Active session UUID.
            chunk_index: Index of the chunk (0-indexed).
            checksum: SHA-256 hash provided in header for verification.
            data: Binary payload of the chunk.

        Returns:
            The updated UploadSession entity.
        """
        log.info(
            "use_case.upload_chunk.start",
            session_id=session_id,
            index=chunk_index,
            size=len(data),
        )

        # 1. Retrieve session
        session = await self.session_repo.get(session_id)
        if not session:
            raise EntityNotFoundError("UploadSession", session_id)

        # 2. Assert valid session state
        if session.status in (UploadStatus.COMPLETED, UploadStatus.ABORTED, UploadStatus.FAILED):
            raise ValidationError(f"Cannot upload chunk: session is in {session.status} state")

        # 3. Concurrency Lock
        locked = await self.session_repo.acquire_lock(session_id)
        if not locked:
            log.error("use_case.upload_chunk.lock_failed", session_id=session_id)
            raise LockAcquisitionError(f"Could not acquire session lock for session {session_id}")

        try:
            # 4. Enforce Chunk Invariants
            chunk_size = len(data)

            # Check maximum size constraint
            if chunk_size > 50 * 1024 * 1024:
                raise ValidationError("Chunk size exceeds maximum limit of 50 MB")

            # Check if this is the final chunk completing the upload
            is_final_chunk = session.current_offset + chunk_size == session.total_size

            # Enforce 5 MB minimum unless it's the final chunk
            if chunk_size < 5 * 1024 * 1024 and not is_final_chunk:
                raise ValidationError(
                    "Intermediate chunks must be at least 5 MB in size "
                    "for S3 Multipart Upload compatibility"
                )

            # 5. Integrity Verification (SHA-256)
            sha256 = hashlib.sha256()
            sha256.update(data)
            calculated_hash = sha256.hexdigest()

            if calculated_hash.lower() != checksum.lower():
                log.error(
                    "use_case.upload_chunk.checksum_mismatch",
                    session_id=session_id,
                    expected=checksum,
                    actual=calculated_hash,
                )
                raise ChecksumMismatchError(
                    f"Checksum mismatch for chunk {chunk_index}. "
                    f"Expected: {checksum}, Calculated: {calculated_hash}"
                )

            # 6. Save Chunk & Update Progress
            chunk = Chunk(
                index=chunk_index,
                size=chunk_size,
                checksum=calculated_hash,
                raw_bytes=data,
            )
            await self.chunk_repo.save(session_id, chunk)

            # Advance offset (internal logic manages status transition)
            session.update_offset(chunk_size)
            await self.session_repo.save(session)

            log.info(
                "use_case.upload_chunk.success",
                session_id=session_id,
                index=chunk_index,
                new_offset=session.current_offset,
            )
            return session

        finally:
            await self.session_repo.release_lock(session_id)
