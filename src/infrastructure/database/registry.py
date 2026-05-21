from uuid import UUID

import structlog
from redis.asyncio import Redis

from domain.protocols.metadata_registry import MetadataRegistry


log = structlog.get_logger(__name__)


class RedisMetadataRegistry(MetadataRegistry):
    """Redis-backed tenant-scoped metadata registry for file deduplication."""

    def __init__(self, redis_client: Redis, ttl_seconds: int | None = None) -> None:
        """Initialize the registry.

        Args:
            redis_client: Active Redis client instance.
            ttl_seconds: Optional TTL for deduplication cache.
        """
        self.redis = redis_client
        self.ttl = ttl_seconds

    def _dedup_key(self, tenant_id: UUID, checksum: str) -> str:
        return f"dedup:{tenant_id}:{checksum}"

    async def get_by_checksum(self, tenant_id: UUID, checksum: str) -> str | None:
        key = self._dedup_key(tenant_id, checksum)
        s3_uri = await self.redis.get(key)
        if s3_uri:
            # Decode if retrieved as bytes
            uri_str = s3_uri.decode("utf-8") if isinstance(s3_uri, bytes) else str(s3_uri)
            log.info("database.dedup.hit", tenant_id=tenant_id, checksum=checksum, s3_uri=uri_str)
            return uri_str

        log.debug("database.dedup.miss", tenant_id=tenant_id, checksum=checksum)
        return None

    async def register_file(
        self,
        tenant_id: UUID,
        file_id: UUID,
        s3_uri: str,
        size: int,
        checksum: str,
    ) -> None:
        key = self._dedup_key(tenant_id, checksum)
        log.info(
            "database.dedup.register",
            tenant_id=tenant_id,
            file_id=file_id,
            checksum=checksum,
            s3_uri=s3_uri,
        )
        if self.ttl:
            await self.redis.set(key, s3_uri, ex=self.ttl)
        else:
            await self.redis.set(key, s3_uri)
