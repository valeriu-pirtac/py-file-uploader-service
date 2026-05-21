"""Application use cases.

Each use case class encapsulates a single business workflow, coordinating
domain entities and infrastructure services via injected protocols.

Example:
    class GetItemUseCase:
        def __init__(self, repository: ItemRepository) -> None:
            self._repository = repository

        async def execute(self, item_id: str) -> ItemDTO:
            item = await self._repository.get(item_id)
            return ItemDTO.from_entity(item)
"""

from application.use_cases.abort import AbortUploadUseCase
from application.use_cases.finalize import FinalizeUploadUseCase
from application.use_cases.initiate import InitiateUploadUseCase
from application.use_cases.upload_chunk import UploadChunkUseCase


__all__: list[str] = [
    "AbortUploadUseCase",
    "FinalizeUploadUseCase",
    "InitiateUploadUseCase",
    "UploadChunkUseCase",
]
