from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    """Represents an individual chunk segment of a file upload."""

    index: int
    size: int
    checksum: str  # Chunk-specific SHA-256 hash
    raw_bytes: bytes
