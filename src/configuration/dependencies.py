from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends
from nats.aio.client import Client
from redis.asyncio import Redis

from application.use_cases.abort import AbortUploadUseCase
from application.use_cases.finalize import FinalizeUploadUseCase
from application.use_cases.initiate import InitiateUploadUseCase
from application.use_cases.upload_chunk import UploadChunkUseCase
from configuration.settings import AppSettings
from domain.protocols.chunk_repository import ChunkRepository
from domain.protocols.event_publisher import EventPublisher
from domain.protocols.metadata_registry import MetadataRegistry
from domain.protocols.object_storage import ObjectStorage
from domain.protocols.session_repository import SessionRepository
from domain.protocols.virus_scanner import VirusScanner
from infrastructure.database.registry import RedisMetadataRegistry
from infrastructure.nats.publisher import NatsEventPublisher
from infrastructure.redis.repository import RedisChunkRepository, RedisSessionRepository
from infrastructure.s3.storage import S3ObjectStorage
from infrastructure.security.scanner import LocalVirusScanner


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Get singleton settings instance."""
    return AppSettings()


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    """Initialize a singleton Redis client based on AppSettings."""
    import redis.asyncio as redis

    settings = get_settings()
    redis_url = f"redis://{settings.redis_host}:{settings.redis_port}"
    return redis.from_url(
        redis_url,
        decode_responses=False,
        socket_connect_timeout=settings.redis_connect_timeout,
    )


@lru_cache(maxsize=1)
def get_s3_client() -> Any:
    """Initialize a singleton S3 client based on AppSettings."""
    import boto3  # type: ignore[import-untyped]
    from botocore.config import Config  # type: ignore[import-untyped]

    settings = get_settings()
    s3_kwargs = {}
    if settings.s3_endpoint_url:
        s3_kwargs["endpoint_url"] = settings.s3_endpoint_url
    if settings.s3_access_key_id:
        s3_kwargs["aws_access_key_id"] = settings.s3_access_key_id
    if settings.s3_secret_access_key:
        s3_kwargs["aws_secret_access_key"] = settings.s3_secret_access_key

    config = Config(connect_timeout=settings.s3_connect_timeout)
    return boto3.client("s3", config=config, **s3_kwargs)


@lru_cache(maxsize=1)
def get_nats_client() -> Client:
    """Initialize, connect, and return a singleton NATS client."""
    return Client()


# Infrastructure Adapters Dependency Injection
def get_session_repository(
    redis_client: Annotated[Redis, Depends(get_redis_client)],
) -> SessionRepository:
    return RedisSessionRepository(redis_client)


def get_chunk_repository(
    redis_client: Annotated[Redis, Depends(get_redis_client)],
) -> ChunkRepository:
    return RedisChunkRepository(redis_client)


def get_object_storage(
    s3_client: Annotated[Any, Depends(get_s3_client)],
    settings: Annotated[AppSettings, Depends(get_settings)],
) -> ObjectStorage:
    return S3ObjectStorage(s3_client, settings.s3_bucket_name)


def get_event_publisher(nats_client: Annotated[Client, Depends(get_nats_client)]) -> EventPublisher:
    return NatsEventPublisher(nats_client)


def get_virus_scanner() -> VirusScanner:
    return LocalVirusScanner()


def get_metadata_registry(
    redis_client: Annotated[Redis, Depends(get_redis_client)],
) -> MetadataRegistry:
    return RedisMetadataRegistry(redis_client)


# Application Use Cases Dependency Injection
def get_initiate_upload_use_case(
    session_repo: Annotated[SessionRepository, Depends(get_session_repository)],
    metadata_registry: Annotated[MetadataRegistry, Depends(get_metadata_registry)],
) -> InitiateUploadUseCase:
    return InitiateUploadUseCase(session_repo, metadata_registry)


def get_upload_chunk_use_case(
    session_repo: Annotated[SessionRepository, Depends(get_session_repository)],
    chunk_repo: Annotated[ChunkRepository, Depends(get_chunk_repository)],
) -> UploadChunkUseCase:
    return UploadChunkUseCase(session_repo, chunk_repo)


def get_finalize_upload_use_case(
    session_repo: Annotated[SessionRepository, Depends(get_session_repository)],
    chunk_repo: Annotated[ChunkRepository, Depends(get_chunk_repository)],
    s3_storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    event_publisher: Annotated[EventPublisher, Depends(get_event_publisher)],
    virus_scanner: Annotated[VirusScanner, Depends(get_virus_scanner)],
    metadata_registry: Annotated[MetadataRegistry, Depends(get_metadata_registry)],
) -> FinalizeUploadUseCase:
    return FinalizeUploadUseCase(
        session_repo=session_repo,
        chunk_repo=chunk_repo,
        s3_storage=s3_storage,
        event_publisher=event_publisher,
        virus_scanner=virus_scanner,
        metadata_registry=metadata_registry,
    )


def get_abort_upload_use_case(
    session_repo: Annotated[SessionRepository, Depends(get_session_repository)],
    chunk_repo: Annotated[ChunkRepository, Depends(get_chunk_repository)],
) -> AbortUploadUseCase:
    return AbortUploadUseCase(session_repo, chunk_repo)
