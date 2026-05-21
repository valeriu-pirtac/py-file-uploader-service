from uuid import UUID, uuid4

import structlog

from domain.entities.upload_session import UploadSession
from domain.protocols.metadata_registry import MetadataRegistry
from domain.protocols.session_repository import SessionRepository
from domain.value_objects.upload_status import UploadStatus


log = structlog.get_logger(__name__)


class InitiateUploadUseCase:
    """Use case to initiate a new chunked upload session or verify deduplication."""

    def __init__(
        self,
        session_repo: SessionRepository,
        metadata_registry: MetadataRegistry,
    ) -> None:
        self.session_repo = session_repo
        self.metadata_registry = metadata_registry

    async def execute(
        self,
        tenant_id: UUID,
        file_id: UUID,
        total_size: int,
        checksum: str,
    ) -> tuple[UploadSession | None, str | None]:
        """Execute the upload initiation workflow.

        Args:
            tenant_id: Tenant UUID.
            file_id: Target file UUID.
            total_size: Total file size in bytes.
            checksum: Full-file SHA-256 hash.

        Returns:
            A tuple of (UploadSession, None) if a new session is created,
            or (None, s3_uri) if the file is successfully deduplicated.
        """
        log.info(
            "use_case.initiate.start",
            tenant_id=tenant_id,
            file_id=file_id,
            total_size=total_size,
        )

        # 1. Deduplication check
        existing_uri = await self.metadata_registry.get_by_checksum(tenant_id, checksum)
        if existing_uri:
            log.info(
                "use_case.initiate.deduplicated",
                tenant_id=tenant_id,
                checksum=checksum,
                s3_uri=existing_uri,
            )
            return None, existing_uri

        # 2. Create new upload session
        session_id = uuid4()
        session = UploadSession(
            session_id=session_id,
            tenant_id=tenant_id,
            file_id=file_id,
            total_size=total_size,
            current_offset=0,
            checksum=checksum,
            status=UploadStatus.INITIATED,
        )

        await self.session_repo.save(session)
        log.info(
            "use_case.initiate.created",
            tenant_id=tenant_id,
            session_id=session_id,
            file_id=file_id,
        )
        return session, None
