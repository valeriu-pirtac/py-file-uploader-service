from uuid import UUID

import structlog

from domain.exceptions import EntityNotFoundError, LockAcquisitionError
from domain.protocols.chunk_repository import ChunkRepository
from domain.protocols.session_repository import SessionRepository


log = structlog.get_logger(__name__)


class AbortUploadUseCase:
    """Use case to abort an active upload session and clean up all cached data."""

    def __init__(
        self,
        session_repo: SessionRepository,
        chunk_repo: ChunkRepository,
    ) -> None:
        self.session_repo = session_repo
        self.chunk_repo = chunk_repo

    async def execute(self, session_id: UUID) -> None:
        """Abort the active session and purge temporary data.

        Args:
            session_id: Active session UUID.
        """
        log.info("use_case.abort.start", session_id=session_id)

        # 1. Retrieve session
        session = await self.session_repo.get(session_id)
        if not session:
            raise EntityNotFoundError("UploadSession", session_id)

        # 2. Concurrency Lock
        locked = await self.session_repo.acquire_lock(session_id)
        if not locked:
            log.error("use_case.abort.lock_failed", session_id=session_id)
            raise LockAcquisitionError(f"Could not acquire session lock for session {session_id}")

        try:
            # 3. Purge cache and session state
            session.abort()
            await self.chunk_repo.delete_all(session_id)
            await self.session_repo.delete(session_id)

            log.info("use_case.abort.success", session_id=session_id)
        finally:
            await self.session_repo.release_lock(session_id)
