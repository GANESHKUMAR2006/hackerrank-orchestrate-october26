"""Pluggable image parser for console screenshots and attachments."""

from __future__ import annotations

from abc import ABC, abstractmethod
import os
from typing import Any, Dict, List, Optional

from code.evidence.parsers.base import BaseEvidenceParser
from code.models import EvidenceManifestEntry, EvidenceObservation


class ImageExtractor(ABC):
    """Abstract interface for image extraction providers (vision models, OCR, metadata)."""

    @abstractmethod
    def extract(
        self,
        file_path: str,
        manifest_entry: Optional[EvidenceManifestEntry] = None,
    ) -> List[EvidenceObservation]:
        """Extract observations from an image file."""
        pass


class MetadataImageExtractor(ImageExtractor):
    """Default extractor when no vision model is configured.

    Retains file and origin metadata while marking visual content as NOT_EXTRACTED
    to prevent hallucinatory findings.
    """

    def extract(
        self,
        file_path: str,
        manifest_entry: Optional[EvidenceManifestEntry] = None,
    ) -> List[EvidenceObservation]:
        evidence_id = manifest_entry.file_id if manifest_entry else ""
        file_ts = manifest_entry.captured_at if manifest_entry else None
        origin = manifest_entry.origin if manifest_entry else "image_store"

        # Determine inferred system from origin or filename
        base_name = os.path.basename(file_path).replace(".png", "").replace(".jpg", "")
        if "account" in base_name:
            system_id = "account_service"
        elif "search" in base_name:
            system_id = "search_service"
        elif "connector" in base_name or "integration" in base_name:
            system_id = "integration_service"
        elif "backup" in base_name:
            system_id = "backup_service"
        elif "support" in base_name:
            system_id = "support_platform"
        elif "analytics" in base_name:
            system_id = "analytics_platform"
        elif "export" in base_name:
            system_id = "export_service"
        elif "security" in base_name:
            system_id = "security_service"
        elif "identity" in base_name or "deleted_account" in base_name:
            system_id = "identity_service"
        else:
            system_id = origin

        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

        obs = EvidenceObservation(
            source_file=file_path,
            evidence_id=evidence_id,
            timestamp=file_ts,
            system_id=system_id,
            resource_id=base_name,
            data_category="CONSOLE_SCREENSHOT",
            extracted_state="NOT_EXTRACTED",
            identifiers={},
            raw_data={
                "extraction_status": "pending_vision",
                "origin": origin,
                "file_size": file_size,
            },
            extraction_method="image_metadata_only",
        )
        return [obs]


class ImageEvidenceParser(BaseEvidenceParser):
    """Parses image evidence using a configured pluggable ImageExtractor."""

    def __init__(self, extractor: Optional[ImageExtractor] = None) -> None:
        super().__init__()
        self.extractor: ImageExtractor = extractor or MetadataImageExtractor()

    def set_extractor(self, extractor: ImageExtractor) -> None:
        """Dynamically plug in a vision or OCR extractor."""
        self.extractor = extractor

    def can_parse(self, file_path: str) -> bool:
        lower = file_path.lower()
        return lower.endswith(".png") or lower.endswith(".jpg") or lower.endswith(".jpeg")

    def parse(
        self,
        file_path: str,
        manifest_entry: Optional[EvidenceManifestEntry] = None,
    ) -> List[EvidenceObservation]:
        try:
            return self.extractor.extract(file_path, manifest_entry)
        except Exception as e:
            self.log_warning(
                file_path=file_path,
                warning_type="IMAGE_PARSE_ERROR",
                message=str(e),
                file_id=manifest_entry.file_id if manifest_entry else None,
            )
            return []
