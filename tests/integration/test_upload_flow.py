"""Integration tests verifying the complete chunked upload ingestion lifecycle."""

import asyncio
import hashlib
import uuid
from typing import Any

import boto3
import nats
import pytest
from fastapi import status
from httpx import AsyncClient

from configuration.settings import AppSettings


def sha256_hex(data: bytes) -> str:
    """Compute sha256 hex checksum of the given bytes."""
    return hashlib.sha256(data).hexdigest()


@pytest.mark.integration
class TestUploadFlowIntegration:
    """High-fidelity end-to-end integration tests verifying the ingest boundary."""

    @pytest.mark.asyncio
    async def test_successful_multipart_upload_and_deduplication(
        self,
        integration_client: AsyncClient,
        test_settings_with_containers: AppSettings,
    ) -> None:
        """Verify the complete successful upload transaction and subsequent deduplication hit."""
        # 1. Setup metadata
        tenant_id = uuid.uuid4()
        file_id = uuid.uuid4()

        # We will upload 3 chunks of 5MB each (S3 minimum is 5MB)
        chunk_size = 5 * 1024 * 1024  # 5 MB
        chunk1_data = b"1" * chunk_size
        chunk2_data = b"2" * chunk_size
        chunk3_data = b"3" * chunk_size

        whole_file_data = chunk1_data + chunk2_data + chunk3_data
        total_size = len(whole_file_data)

        whole_file_checksum = sha256_hex(whole_file_data)
        chunk1_checksum = sha256_hex(chunk1_data)
        chunk2_checksum = sha256_hex(chunk2_data)
        chunk3_checksum = sha256_hex(chunk3_data)

        headers = {"Authorization": f"Bearer {tenant_id}"}

        # -------------------------------------------------------------
        # STEP 1: INITIATE UPLOAD
        # -------------------------------------------------------------
        init_payload = {
            "file_id": str(file_id),
            "total_size": total_size,
            "checksum": whole_file_checksum,
        }

        init_resp = await integration_client.post(
            "/v1/uploads",
            json=init_payload,
            headers=headers,
        )
        assert init_resp.status_code == status.HTTP_201_CREATED
        init_data = init_resp.json()
        assert init_data["upload_session_id"] is not None
        assert not init_data["deduplicated"]
        assert init_data["s3_uri"] is None

        session_id = uuid.UUID(init_data["upload_session_id"])

        # -------------------------------------------------------------
        # STEP 2: UPLOAD CHUNKS
        # -------------------------------------------------------------
        # Chunk 0
        resp_c0 = await integration_client.patch(
            f"/v1/uploads/{session_id}?index=0",
            content=chunk1_data,
            headers={
                **headers,
                "X-Chunk-Checksum": chunk1_checksum,
                "Content-Type": "application/octet-stream",
            },
        )
        assert resp_c0.status_code == status.HTTP_200_OK
        assert resp_c0.json()["current_offset"] == chunk_size
        assert resp_c0.json()["status"] == "active"

        # Chunk 1
        resp_c1 = await integration_client.patch(
            f"/v1/uploads/{session_id}?index=1",
            content=chunk2_data,
            headers={
                **headers,
                "X-Chunk-Checksum": chunk2_checksum,
                "Content-Type": "application/octet-stream",
            },
        )
        assert resp_c1.status_code == status.HTTP_200_OK
        assert resp_c1.json()["current_offset"] == chunk_size * 2
        assert resp_c1.json()["status"] == "active"

        # Chunk 2
        resp_c2 = await integration_client.patch(
            f"/v1/uploads/{session_id}?index=2",
            content=chunk3_data,
            headers={
                **headers,
                "X-Chunk-Checksum": chunk3_checksum,
                "Content-Type": "application/octet-stream",
            },
        )
        assert resp_c2.status_code == status.HTTP_200_OK
        assert resp_c2.json()["current_offset"] == total_size
        assert resp_c2.json()["status"] == "completed"

        # -------------------------------------------------------------
        # STEP 3: QUERY SESSION STATE (HEAD)
        # -------------------------------------------------------------
        head_resp = await integration_client.head(
            f"/v1/uploads/{session_id}",
            headers=headers,
        )
        assert head_resp.status_code == status.HTTP_200_OK
        assert head_resp.headers["Upload-Offset"] == str(total_size)
        assert head_resp.headers["Upload-Length"] == str(total_size)
        assert head_resp.headers["Upload-Status"] == "completed"

        # Subscribe to NATS for validation
        nc = await nats.connect(test_settings_with_containers.nats_url)
        nats_future = asyncio.get_running_loop().create_future()

        async def event_handler(msg: Any) -> None:
            import json

            payload = json.loads(msg.data.decode("utf-8"))
            nats_future.set_result(payload)

        sub = await nc.subscribe("FILE_UPLOAD_COMPLETED", cb=event_handler)

        # -------------------------------------------------------------
        # STEP 4: FINALIZE UPLOAD
        # -------------------------------------------------------------
        finalize_resp = await integration_client.post(
            f"/v1/uploads/{session_id}/finalize",
            headers=headers,
        )
        assert finalize_resp.status_code == status.HTTP_200_OK
        finalize_data = finalize_resp.json()
        assert finalize_data["s3_uri"] is not None
        expected_s3_uri = (
            f"s3://{test_settings_with_containers.s3_bucket_name}/uploads/{tenant_id}/raw/{file_id}"
        )
        assert finalize_data["s3_uri"] == expected_s3_uri

        # -------------------------------------------------------------
        # STEP 5: VERIFY S3 PERSISTENCE
        # -------------------------------------------------------------
        s3 = boto3.client(
            "s3",
            endpoint_url=test_settings_with_containers.s3_endpoint_url,
            aws_access_key_id=test_settings_with_containers.s3_access_key_id,
            aws_secret_access_key=test_settings_with_containers.s3_secret_access_key,
        )

        s3_resp = s3.get_object(
            Bucket=test_settings_with_containers.s3_bucket_name,
            Key=f"uploads/{tenant_id}/raw/{file_id}",
        )
        persisted_content = s3_resp["Body"].read()
        assert persisted_content == whole_file_data

        # -------------------------------------------------------------
        # STEP 6: VERIFY NATS EVENT DELIVERY
        # -------------------------------------------------------------
        nats_payload = await asyncio.wait_for(nats_future, timeout=2.0)
        assert nats_payload["tenant_id"] == str(tenant_id)
        assert nats_payload["file_id"] == str(file_id)
        assert nats_payload["s3_uri"] == expected_s3_uri
        assert nats_payload["total_size"] == total_size
        assert nats_payload["checksum"] == whole_file_checksum

        await sub.unsubscribe()
        await nc.close()

        # -------------------------------------------------------------
        # STEP 7: VERIFY METADATA DEDUPLICATION HIT
        # -------------------------------------------------------------
        new_file_id = uuid.uuid4()
        dedup_resp = await integration_client.post(
            "/v1/uploads",
            json={
                "file_id": str(new_file_id),
                "total_size": total_size,
                "checksum": whole_file_checksum,
            },
            headers=headers,
        )
        assert dedup_resp.status_code == status.HTTP_200_OK
        dedup_data = dedup_resp.json()
        assert dedup_data["upload_session_id"] is None
        assert dedup_data["deduplicated"]
        assert dedup_data["s3_uri"] == expected_s3_uri

    @pytest.mark.asyncio
    async def test_checksum_mismatch_failure(
        self,
        integration_client: AsyncClient,
        test_settings_with_containers: AppSettings,
    ) -> None:
        """Verify that uploading a chunk with a mismatched checksum returns HTTP 460."""
        tenant_id = uuid.uuid4()
        file_id = uuid.uuid4()

        headers = {"Authorization": f"Bearer {tenant_id}"}

        init_resp = await integration_client.post(
            "/v1/uploads",
            json={
                "file_id": str(file_id),
                "total_size": 10,
                "checksum": "a" * 64,
            },
            headers=headers,
        )
        assert init_resp.status_code == status.HTTP_201_CREATED
        session_id = init_resp.json()["upload_session_id"]

        # PATCH with bad chunk checksum
        resp = await integration_client.patch(
            f"/v1/uploads/{session_id}?index=0",
            content=b"some bytes",
            headers={
                **headers,
                "X-Chunk-Checksum": "bad-checksum-value",
                "Content-Type": "application/octet-stream",
            },
        )
        # Custom Tus-inspired mismatch code
        assert resp.status_code == 460
        assert "mismatch" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_malware_detection_rejection(
        self,
        integration_client: AsyncClient,
        test_settings_with_containers: AppSettings,
    ) -> None:
        """Verify that uploading standard EICAR malware signature fails finalization with HTTP 422."""
        tenant_id = uuid.uuid4()
        file_id = uuid.uuid4()

        # EICAR signature is standard anti-malware test signature
        eicar_signature = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

        headers = {"Authorization": f"Bearer {tenant_id}"}

        init_resp = await integration_client.post(
            "/v1/uploads",
            json={
                "file_id": str(file_id),
                "total_size": len(eicar_signature),
                "checksum": sha256_hex(eicar_signature),
            },
            headers=headers,
        )
        assert init_resp.status_code == status.HTTP_201_CREATED
        session_id = init_resp.json()["upload_session_id"]

        # Upload EICAR chunk
        resp = await integration_client.patch(
            f"/v1/uploads/{session_id}?index=0",
            content=eicar_signature,
            headers={
                **headers,
                "X-Chunk-Checksum": sha256_hex(eicar_signature),
                "Content-Type": "application/octet-stream",
            },
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "completed"

        # Finalize should trigger virus scan and fail
        finalize_resp = await integration_client.post(
            f"/v1/uploads/{session_id}/finalize",
            headers=headers,
        )
        assert finalize_resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert "malware" in finalize_resp.json()["detail"].lower()
