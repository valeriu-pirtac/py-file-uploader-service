"""Pytest configuration and shared fixtures for integration tests."""

import socket
import time
from collections.abc import Generator

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.minio import MinioContainer

from configuration.settings import AppSettings


def wait_for_port(host: str, port: int, timeout: float = 5.0) -> bool:
    """Wait until a port is open and accepting TCP connections."""
    start_time = time.monotonic()
    while time.monotonic() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.05)
    return False


@pytest.fixture(scope="session")
def redis_container() -> Generator[DockerContainer]:
    """Yield a running Redis container.

    Uses redis:7.2-alpine as a lightweight, fast-starting Redis instance.
    """
    with DockerContainer("redis:7.2-alpine").with_exposed_ports(6379) as container:
        host = container.get_container_host_ip()
        port = int(container.get_exposed_port(6379))
        if not wait_for_port(host, port):
            raise RuntimeError("Redis container did not start in time")
        yield container


@pytest.fixture(scope="session")
def minio_container() -> Generator[MinioContainer]:
    """Yield a running MinIO container.

    Uses minio/minio image to replicate S3 API compatibility.
    """
    with MinioContainer() as container:
        yield container


@pytest.fixture(scope="session")
def nats_container() -> Generator[DockerContainer]:
    """Yield a running NATS container.

    Uses the official nats image.
    """
    with DockerContainer("nats:latest").with_exposed_ports(4222) as container:
        host = container.get_container_host_ip()
        port = int(container.get_exposed_port(4222))
        if not wait_for_port(host, port):
            raise RuntimeError("NATS container did not start in time")
        yield container


@pytest.fixture(scope="session")
def test_settings_with_containers(
    redis_container: DockerContainer,
    minio_container: MinioContainer,
    nats_container: DockerContainer,
) -> AppSettings:
    """Return AppSettings dynamically configured to point to the live test containers."""
    redis_host = redis_container.get_container_host_ip()
    redis_port = int(redis_container.get_exposed_port(6379))

    nats_host = nats_container.get_container_host_ip()
    nats_port = int(nats_container.get_exposed_port(4222))

    return AppSettings(
        log_level="DEBUG",
        log_format="console",
        metrics_enabled=False,
        host="127.0.0.1",
        port=8000,
        workers=1,
        redis_host=redis_host,
        redis_port=redis_port,
        s3_endpoint_url=f"http://{minio_container.get_config()['endpoint']}",
        s3_access_key_id=minio_container.get_config()["access_key"],
        s3_secret_access_key=minio_container.get_config()["secret_key"],
        s3_bucket_name="bronze-file-uploads-test",
        nats_url=f"nats://{nats_host}:{nats_port}",
    )
