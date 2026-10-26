"""Base parser interface and warning handling for evidence extraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from code.models import EvidenceManifestEntry, EvidenceObservation, IngestionWarning


class BaseEvidenceParser(ABC):
    """Abstract base class for format-specific evidence parsers."""

    def __init__(self) -> None:
        self.warnings: List[IngestionWarning] = []

    def log_warning(
        self,
        file_path: str,
        warning_type: str,
        message: str,
        file_id: Optional[str] = None,
    ) -> None:
        """Record a structured warning without failing execution."""
        self.warnings.append(
            IngestionWarning(
                file_id=file_id,
                file_path=file_path,
                warning_type=warning_type,
                message=message,
            )
        )

    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """Return True if this parser supports the given file format/path."""
        pass

    @abstractmethod
    def parse(
        self,
        file_path: str,
        manifest_entry: Optional[EvidenceManifestEntry] = None,
    ) -> List[EvidenceObservation]:
        """Extract structured observations from the given file."""
        pass
