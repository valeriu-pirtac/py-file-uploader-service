"""Domain protocols (interfaces).

Define abstract interfaces (using typing.Protocol or abc.ABC) that the
infrastructure layer must implement.

Example:
    class ItemRepository(Protocol):
        async def get(self, item_id: str) -> Item: ...
        async def save(self, item: Item) -> None: ...
"""

from domain.protocols.chunk_repository import ChunkRepository
from domain.protocols.event_publisher import EventPublisher
from domain.protocols.metadata_registry import MetadataRegistry
from domain.protocols.object_storage import ObjectStorage
from domain.protocols.session_repository import SessionRepository
from domain.protocols.virus_scanner import VirusScanner


__all__: list[str] = [
    "SessionRepository",
    "ChunkRepository",
    "ObjectStorage",
    "EventPublisher",
    "VirusScanner",
    "MetadataRegistry",
]
