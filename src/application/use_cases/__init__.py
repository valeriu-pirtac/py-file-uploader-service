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

__all__: list[str] = []
