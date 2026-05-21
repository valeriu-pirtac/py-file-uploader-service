from collections.abc import AsyncIterator
from typing import Protocol


class VirusScanner(Protocol):
    """Abstract protocol for in-stream malware scanning."""

    async def scan_stream(self, stream_iterator: AsyncIterator[bytes]) -> bool:
        """Scan a binary stream for malware signature patterns.

        Returns:
            True if the stream is clean.

        Raises:
            MalwareDetectedError: If malware is detected in the stream.
        """
        ...
