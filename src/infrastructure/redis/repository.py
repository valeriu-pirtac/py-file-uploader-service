import json
from collections.abc import AsyncIterator
from uuid import UUID

import structlog
from redis.asyncio import Redis

from domain.entities.chunk import Chunk
from domain.entities.upload_session import UploadSession
from domain.protocols.chunk_repository import ChunkRepository
from domain.protocols.session_repository import SessionRepository
from domain.value_objects.upload_status import UploadStatus


log = structlog.get_logger(__name__)


class RedisSessionRepository(SessionRepository):
    """Redis-backed implementation of the SessionRepository protocol."""

    def __init__(self, redis_client: Redis, ttl_seconds: int = 86400) -> None:
        """Initialize the repository.

        Args:
            redis_client: Redis client connection.
            ttl_seconds: TTL for session keys (defaults to 24 hours).
        """
        self.redis = redis_client
        self.ttl = ttl_seconds

    def _session_key(self, session_id: UUID) -> str:
        return f"session:upload:{session_id}"

    def _lock_key(self, session_id: UUID) -> str:
        return f"lock:upload:{session_id}"

    async def get(self, session_id: UUID) -> UploadSession | None:
        key = self._session_key(session_id)
        data = await self.redis.get(key)
        if not data:
            return None

        try:
            payload = json.loads(data)
            return UploadSession(
                session_id=UUID(payload["session_id"]),
                tenant_id=UUID(payload["tenant_id"]),
                file_id=UUID(payload["file_id"]),
                total_size=int(payload["total_size"]),
                current_offset=int(payload["current_offset"]),
                checksum=payload["checksum"],
                status=UploadStatus(payload["status"]),
            )
        except Exception as e:
            log.error("redis.session.deserialize.failed", session_id=session_id, error=str(e))
            return None

    async def save(self, session: UploadSession) -> None:
        key = self._session_key(session.session_id)
        payload = {
            "session_id": str(session.session_id),
            "tenant_id": str(session.tenant_id),
            "file_id": str(session.file_id),
            "total_size": session.total_size,
            "current_offset": session.current_offset,
            "checksum": session.checksum,
            "status": session.status.value,
        }
        await self.redis.set(key, json.dumps(payload), ex=self.ttl)

    async def delete(self, session_id: UUID) -> None:
        key = self._session_key(session_id)
        await self.redis.delete(key)

    async def acquire_lock(self, session_id: UUID, ttl_seconds: int = 10) -> bool:
        lock_key = self._lock_key(session_id)
        # SET NX EX
        acquired = await self.redis.set(lock_key, "locked", ex=ttl_seconds, nx=True)
        return bool(acquired)

    async def release_lock(self, session_id: UUID) -> None:
        lock_key = self._lock_key(session_id)
        await self.redis.delete(lock_key)


class RedisChunkRepository(ChunkRepository):
    """Redis-backed implementation of the ChunkRepository protocol."""

    def __init__(self, redis_client: Redis, ttl_seconds: int = 86400) -> None:
        """Initialize the repository.

        Args:
            redis_client: Redis client connection.
            ttl_seconds: TTL for cached chunks (defaults to 24 hours).
        """
        self.redis = redis_client
        self.ttl = ttl_seconds

    def _chunk_key(self, session_id: UUID, index: int) -> str:
        return f"upload:{session_id}:chunk:{index}"

    def _chunk_meta_key(self, session_id: UUID, index: int) -> str:
        return f"upload:{session_id}:chunk_meta:{index}"

    async def save(self, session_id: UUID, chunk: Chunk) -> None:
        chunk_key = self._chunk_key(session_id, chunk.index)
        meta_key = self._chunk_meta_key(session_id, chunk.index)

        # Store binary payload and its checksum/metadata
        async with self.redis.pipeline() as pipe:
            pipe.set(chunk_key, chunk.raw_bytes, ex=self.ttl)
            pipe.set(
                meta_key,
                json.dumps({"checksum": chunk.checksum, "size": chunk.size}),
                ex=self.ttl,
            )
            await pipe.execute()

    async def get(self, session_id: UUID, index: int) -> Chunk | None:
        chunk_key = self._chunk_key(session_id, index)
        meta_key = self._chunk_meta_key(session_id, index)

        raw_bytes = await self.redis.get(chunk_key)
        meta_data = await self.redis.get(meta_key)

        if not raw_bytes or not meta_data:
            return None

        try:
            meta = json.loads(meta_data)
            return Chunk(
                index=index,
                size=int(meta["size"]),
                checksum=meta["checksum"],
                raw_bytes=raw_bytes,
            )
        except Exception as e:
            log.error(
                "redis.chunk.deserialize.failed",
                session_id=session_id,
                index=index,
                error=str(e),
            )
            return None

    async def get_stream(self, session_id: UUID) -> AsyncIterator[bytes]:
        index = 0
        while True:
            chunk_key = self._chunk_key(session_id, index)
            chunk_bytes = await self.redis.get(chunk_key)
            if not chunk_bytes:
                break
            yield chunk_bytes
            index += 1

    async def delete_all(self, session_id: UUID) -> None:
        # Find all keys belonging to this session and delete them
        pattern = f"upload:{session_id}:*"
        keys = []
        async for key in self.redis.scan_iter(pattern):
            keys.append(key)

        if keys:
            await self.redis.delete(*keys)
