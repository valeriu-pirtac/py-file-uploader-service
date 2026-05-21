import asyncio
import json
from uuid import UUID

import structlog
from nats.aio.client import Client

from domain.protocols.event_publisher import EventPublisher


log = structlog.get_logger(__name__)


class NatsEventPublisher(EventPublisher):
    """NATS JetStream/Core event publisher implementation with client-side retry logic."""

    def __init__(
        self,
        nats_client: Client,
        subject: str = "FILE_UPLOAD_COMPLETED",
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
    ) -> None:
        """Initialize the NATS publisher.

        Args:
            nats_client: Pre-connected active NATS client instance.
            subject: Subject name to publish events to.
            max_retries: Number of publication retries before failing.
            retry_delay_seconds: Initial backoff delay for retries.
        """
        self.nc = nats_client
        self.subject = subject
        self.max_retries = max_retries
        self.retry_delay = retry_delay_seconds

    async def publish_file_upload_completed(
        self,
        tenant_id: UUID,
        file_id: UUID,
        s3_uri: str,
        total_size: int,
        checksum: str,
    ) -> None:
        payload = {
            "tenant_id": str(tenant_id),
            "file_id": str(file_id),
            "s3_uri": s3_uri,
            "total_size": total_size,
            "checksum": checksum,
        }
        payload_bytes = json.dumps(payload).encode("utf-8")

        log.info(
            "nats.event.publish.attempt",
            subject=self.subject,
            tenant_id=tenant_id,
            file_id=file_id,
        )

        attempt = 0
        while True:
            try:
                # Ensure the client is active and connected
                if not self.nc.is_connected and not self.nc.is_reconnecting:
                    raise ConnectionError("NATS client is disconnected")

                await self.nc.publish(self.subject, payload_bytes)
                # Flush to ensure event is sent to broker successfully
                await self.nc.flush()
                log.info(
                    "nats.event.publish.success",
                    subject=self.subject,
                    tenant_id=tenant_id,
                    file_id=file_id,
                )
                return
            except Exception as e:
                attempt += 1
                log.warn(
                    "nats.event.publish.failed",
                    subject=self.subject,
                    attempt=attempt,
                    error=str(e),
                )
                if attempt >= self.max_retries:
                    log.error(
                        "nats.event.publish.failed.exhausted",
                        subject=self.subject,
                        tenant_id=tenant_id,
                        file_id=file_id,
                    )
                    raise RuntimeError(
                        f"Failed to publish event to NATS after {self.max_retries} attempts: {e}"
                    ) from e

                # Exponential backoff
                await asyncio.sleep(self.retry_delay * (2 ** (attempt - 1)))
