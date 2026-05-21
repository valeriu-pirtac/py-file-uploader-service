import asyncio
from typing import Any
from uuid import UUID

import structlog

from domain.protocols.object_storage import ObjectStorage


log = structlog.get_logger(__name__)


class S3ObjectStorage(ObjectStorage):
    """S3-backed implementation of the ObjectStorage protocol using boto3 client."""

    def __init__(self, s3_client: Any, bucket_name: str) -> None:
        """Initialize the storage adapter.

        Args:
            s3_client: Pre-configured boto3 S3 client.
            bucket_name: Name of the target S3 bucket.
        """
        self.s3 = s3_client
        self.bucket = bucket_name

    def _object_key(self, tenant_id: UUID, file_id: UUID) -> str:
        return f"uploads/{tenant_id}/raw/{file_id}"

    async def initiate_multipart_upload(self, tenant_id: UUID, file_id: UUID) -> str:
        key = self._object_key(tenant_id, file_id)
        log.info("s3.multipart.initiate", tenant_id=tenant_id, file_id=file_id, key=key)

        def _initiate() -> str:
            response = self.s3.create_multipart_upload(Bucket=self.bucket, Key=key)
            return str(response["UploadId"])

        return await asyncio.to_thread(_initiate)

    async def upload_part(
        self,
        tenant_id: UUID,
        file_id: UUID,
        upload_id: str,
        part_number: int,
        data: bytes,
    ) -> dict[str, Any]:
        key = self._object_key(tenant_id, file_id)
        log.debug(
            "s3.multipart.upload_part",
            tenant_id=tenant_id,
            file_id=file_id,
            part_number=part_number,
        )

        def _upload() -> dict[str, Any]:
            response = self.s3.upload_part(
                Bucket=self.bucket,
                Key=key,
                UploadId=upload_id,
                PartNumber=part_number,
                Body=data,
            )
            # Must return ETag and PartNumber in correct format for completion
            return {"ETag": response["ETag"], "PartNumber": part_number}

        return await asyncio.to_thread(_upload)

    async def complete_multipart_upload(
        self,
        tenant_id: UUID,
        file_id: UUID,
        upload_id: str,
        parts: list[dict[str, Any]],
    ) -> str:
        key = self._object_key(tenant_id, file_id)
        log.info("s3.multipart.complete", tenant_id=tenant_id, file_id=file_id)

        # Parts must be sorted by PartNumber for S3 API compliance
        sorted_parts = sorted(parts, key=lambda p: p["PartNumber"])

        def _complete() -> str:
            self.s3.complete_multipart_upload(
                Bucket=self.bucket,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={"Parts": sorted_parts},
            )
            # Return final S3 URI reference
            return f"s3://{self.bucket}/{key}"

        return await asyncio.to_thread(_complete)

    async def abort_multipart_upload(self, tenant_id: UUID, file_id: UUID, upload_id: str) -> None:
        key = self._object_key(tenant_id, file_id)
        log.warn("s3.multipart.abort", tenant_id=tenant_id, file_id=file_id)

        def _abort() -> None:
            try:
                self.s3.abort_multipart_upload(Bucket=self.bucket, Key=key, UploadId=upload_id)
            except Exception as e:
                log.error("s3.multipart.abort.failed", error=str(e))

        await asyncio.to_thread(_abort)
