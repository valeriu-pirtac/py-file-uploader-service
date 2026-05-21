from uuid import UUID

import structlog

from domain.exceptions import (
    EntityNotFoundError,
    LockAcquisitionError,
    MalwareDetectedError,
    ValidationError,
)
from domain.protocols.chunk_repository import ChunkRepository
from domain.protocols.event_publisher import EventPublisher
from domain.protocols.metadata_registry import MetadataRegistry
from domain.protocols.object_storage import ObjectStorage
from domain.protocols.session_repository import SessionRepository
from domain.protocols.virus_scanner import VirusScanner
from domain.value_objects.upload_status import UploadStatus


log = structlog.get_logger(__name__)


class FinalizeUploadUseCase:
    """Use case to scan, assemble, persist to S3, and trigger downstream processing."""

    def __init__(
        self,
        session_repo: SessionRepository,
        chunk_repo: ChunkRepository,
        s3_storage: ObjectStorage,
        event_publisher: EventPublisher,
        virus_scanner: VirusScanner,
        metadata_registry: MetadataRegistry,
    ) -> None:
        self.session_repo = session_repo
        self.chunk_repo = chunk_repo
        self.s3_storage = s3_storage
        self.event_publisher = event_publisher
        self.virus_scanner = virus_scanner
        self.metadata_registry = metadata_registry

    async def execute(self, session_id: UUID) -> str:
        """Scan, assemble, commit to S3, register deduplication, and publish event.

        Args:
            session_id: Active session UUID.

        Returns:
            The final S3 URI reference of the committed file.
        """
        log.info("use_case.finalize.start", session_id=session_id)

        # 1. Retrieve session
        session = await self.session_repo.get(session_id)
        if not session:
            raise EntityNotFoundError("UploadSession", session_id)

        if session.status == UploadStatus.COMPLETED:
            raise ValidationError("Upload session has already been completed.")
        if session.status in (UploadStatus.ABORTED, UploadStatus.FAILED):
            raise ValidationError(f"Cannot finalize: session is in {session.status} state")

        # 2. Check offset compliance
        if session.current_offset != session.total_size:
            raise ValidationError(
                f"Cannot finalize: not all bytes have been uploaded. "
                f"Uploaded offset: {session.current_offset}, Expected total size: {session.total_size}"
            )

        # 3. Concurrency Lock
        locked = await self.session_repo.acquire_lock(session_id)
        if not locked:
            log.error("use_case.finalize.lock_failed", session_id=session_id)
            raise LockAcquisitionError(f"Could not acquire session lock for session {session_id}")

        try:
            # 4. In-stream Virus Scanning
            # Pull sequential chunks and feed them through the scanner stream
            stream = self.chunk_repo.get_stream(session_id)
            try:
                await self.virus_scanner.scan_stream(stream)
            except MalwareDetectedError as threat:
                log.error("use_case.finalize.malware_detected", session_id=session_id)
                # Purge session chunk keys and mark failed
                session.fail()
                await self.session_repo.save(session)
                await self.chunk_repo.delete_all(session_id)
                await self.session_repo.delete(session_id)
                raise threat

            # 5. S3 Multipart Stream Orchestration
            upload_id = await self.s3_storage.initiate_multipart_upload(
                session.tenant_id, session.file_id
            )
            parts = []
            part_number = 1

            try:
                while True:
                    chunk = await self.chunk_repo.get(session_id, part_number - 1)
                    if not chunk:
                        break

                    part = await self.s3_storage.upload_part(
                        tenant_id=session.tenant_id,
                        file_id=session.file_id,
                        upload_id=upload_id,
                        part_number=part_number,
                        data=chunk.raw_bytes,
                    )
                    parts.append(part)
                    part_number += 1

                # Complete the upload
                s3_uri = await self.s3_storage.complete_multipart_upload(
                    session.tenant_id, session.file_id, upload_id, parts
                )
            except Exception as s3_error:
                log.error("use_case.finalize.s3_multipart_failed", error=str(s3_error))
                # Cleanup S3 state
                await self.s3_storage.abort_multipart_upload(
                    session.tenant_id, session.file_id, upload_id
                )
                session.fail()
                await self.session_repo.save(session)
                raise RuntimeError(f"S3 Multipart upload failed: {s3_error}") from s3_error

            # 6. Deduplication Registration
            await self.metadata_registry.register_file(
                tenant_id=session.tenant_id,
                file_id=session.file_id,
                s3_uri=s3_uri,
                size=session.total_size,
                checksum=session.checksum,
            )

            # 7. Downstream Ingestion Trigger
            await self.event_publisher.publish_file_upload_completed(
                tenant_id=session.tenant_id,
                file_id=session.file_id,
                s3_uri=s3_uri,
                total_size=session.total_size,
                checksum=session.checksum,
            )

            # 8. Clean up Redis State
            session.complete()
            await self.chunk_repo.delete_all(session_id)
            await self.session_repo.delete(session_id)

            log.info("use_case.finalize.success", session_id=session_id, s3_uri=s3_uri)
            return s3_uri

        finally:
            await self.session_repo.release_lock(session_id)
