"""Domain protocols (interfaces).

Define abstract interfaces (using typing.Protocol or abc.ABC) that the
infrastructure layer must implement.

Example:
    class ItemRepository(Protocol):
        async def get(self, item_id: str) -> Item: ...
        async def save(self, item: Item) -> None: ...
"""

__all__: list[str] = []
