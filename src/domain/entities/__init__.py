"""Domain entities.

Entities are objects with a unique identity that persists over time.
Place concrete entity classes (e.g. Item, Order, User) in this package.
"""

from domain.entities.chunk import Chunk
from domain.entities.upload_session import UploadSession


__all__: list[str] = ["UploadSession", "Chunk"]
