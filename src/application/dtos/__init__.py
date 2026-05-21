"""Data Transfer Objects (DTOs).

DTOs carry data between layers without exposing domain internals.
Use Pydantic BaseModel for automatic validation and serialization.

Example:
    class ItemDTO(BaseModel):
        id: str
        name: str
"""

__all__: list[str] = []
