from collections.abc import AsyncIterator

import structlog

from domain.exceptions import MalwareDetectedError
from domain.protocols.virus_scanner import VirusScanner


log = structlog.get_logger(__name__)


class LocalVirusScanner(VirusScanner):
    """In-stream virus scanner simulating real-time scanning.

    Scans for the EICAR standard anti-malware test signature in the streamed bytes.
    """

    def __init__(self) -> None:
        # Standard EICAR signature snippet to match against
        self.eicar_signature = b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE"

    async def scan_stream(self, stream_iterator: AsyncIterator[bytes]) -> bool:
        log.info("security.virus_scan.start")

        async for chunk in stream_iterator:
            if self.eicar_signature in chunk:
                log.error("security.virus_scan.threat_detected", threat="EICAR-Test-Signature")
                raise MalwareDetectedError(
                    "Malware Signature Detected: EICAR standard anti-virus test file."
                )

        log.info("security.virus_scan.clean")
        return True
