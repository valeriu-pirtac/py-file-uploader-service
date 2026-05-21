"""Integration tests verifying connection and interaction with live containerized dependencies."""

import boto3
import nats
import pytest
import redis

from configuration.settings import AppSettings


@pytest.mark.integration
class TestRedisIntegration:
    """Integration tests verifying operations on the live Redis container."""

    def test_redis_connection_and_operations(
        self, test_settings_with_containers: AppSettings
    ) -> None:
        """Verify we can establish a connection and perform get/set operations on Redis."""
        # Initialize client using dynamically wired ports
        client: redis.Redis = redis.Redis(
            host=test_settings_with_containers.redis_host,
            port=test_settings_with_containers.redis_port,
            decode_responses=True,
        )

        # Test simple Key-Value lifecycle
        test_key = "integration_test:session:123"
        test_value = "chunk_offset_10240"

        client.set(test_key, test_value, ex=60)
        assert client.get(test_key) == test_value

        # Clean up
        client.delete(test_key)
        assert client.get(test_key) is None


@pytest.mark.integration
class TestMinioS3Integration:
    """Integration tests verifying operations on the live MinIO S3 object store."""

    def test_s3_connection_and_multipart(self, test_settings_with_containers: AppSettings) -> None:
        """Verify S3 operations, including bucket creation and object upload/download."""
        s3 = boto3.client(
            "s3",
            endpoint_url=test_settings_with_containers.s3_endpoint_url,
            aws_access_key_id=test_settings_with_containers.s3_access_key_id,
            aws_secret_access_key=test_settings_with_containers.s3_secret_access_key,
        )

        bucket_name = test_settings_with_containers.s3_bucket_name
        test_key = "uploads/raw/test-document.pdf"
        test_content = b"%PDF-1.4 - Ephemeral Test File Content for Ingestion"

        # 1. Create a raw bronze-layer storage bucket
        s3.create_bucket(Bucket=bucket_name)

        # 2. Put file to bucket
        s3.put_object(Bucket=bucket_name, Key=test_key, Body=test_content)

        # 3. Read back file and assert contents match
        response = s3.get_object(Bucket=bucket_name, Key=test_key)
        downloaded_content = response["Body"].read()

        assert downloaded_content == test_content

        # 4. Clean up object and bucket
        s3.delete_object(Bucket=bucket_name, Key=test_key)
        s3.delete_bucket(Bucket=bucket_name)


@pytest.mark.integration
class TestNatsIntegration:
    """Integration tests verifying operations on the live NATS broker container."""

    @pytest.mark.asyncio
    async def test_nats_connection_publish_subscribe(
        self, test_settings_with_containers: AppSettings
    ) -> None:
        """Verify NATS broker connection, message publishing, and subscription."""
        # Initialize client connecting to the dynamically mapped container URI
        nc = await nats.connect(test_settings_with_containers.nats_url)

        # Set up a message receiver/future
        import asyncio

        received_messages = []
        future = asyncio.get_running_loop().create_future()

        async def message_handler(msg) -> None:
            received_messages.append(msg.data)
            future.set_result(True)

        # Subscribe to a test subject
        sub = await nc.subscribe("integration_test.uploads", cb=message_handler)

        # Publish a sample event payload
        test_payload = b'{"event": "FILE_UPLOAD_COMPLETED", "file_id": "999"}'
        await nc.publish("integration_test.uploads", test_payload)
        await nc.flush()

        # Wait for the future to resolve with a timeout
        await asyncio.wait_for(future, timeout=2.0)

        # Assertions
        assert len(received_messages) == 1
        assert received_messages[0] == test_payload

        # Clean up connection
        await sub.unsubscribe()
        await nc.close()
