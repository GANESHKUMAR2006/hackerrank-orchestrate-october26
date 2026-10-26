"""PDF document parser extracting text, metadata, and structured entities."""

from __future__ import annotations

from datetime import datetime
import re
from typing import Dict, List, Optional, Set

from code.evidence.parsers.base import BaseEvidenceParser
from code.models import EvidenceManifestEntry, EvidenceObservation

try:
    import pymupdf  # type: ignore
except ImportError:
    pymupdf = None


class PDFEvidenceParser(BaseEvidenceParser):
    """Parses PDF documents using PyMuPDF (fitz)."""

    EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    USER_ID_REGEX = re.compile(r"\buser_\d+\b")
    RESOURCE_ID_REGEX = re.compile(r"\b(?:support|account|audit_record|analytics|backup|export|data_flow|statement|tombstone|search)_\w+\b")

    def can_parse(self, file_path: str) -> bool:
        return file_path.lower().endswith(".pdf")

    def parse(
        self,
        file_path: str,
        manifest_entry: Optional[EvidenceManifestEntry] = None,
    ) -> List[EvidenceObservation]:
        observations: List[EvidenceObservation] = []
        evidence_id = manifest_entry.file_id if manifest_entry else ""
        file_ts = manifest_entry.captured_at if manifest_entry else None

        if pymupdf is None:
            self.log_warning(
                file_path=file_path,
                warning_type="MISSING_DEPENDENCY",
                message="PyMuPDF is not installed. PDF extraction skipped.",
                file_id=evidence_id,
            )
            return observations

        try:
            doc = pymupdf.open(file_path)
            full_text = "\n".join([page.get_text() for page in doc])

            # Extract distinct identifiers
            emails = set(self.EMAIL_REGEX.findall(full_text))
            user_ids = set(self.USER_ID_REGEX.findall(full_text))
            resource_ids = set(self.RESOURCE_ID_REGEX.findall(full_text))

            # Infer system
            system_id = "document_service"
            category = "DOCUMENT"
            lower_path = file_path.lower()

            if "delivery" in lower_path or "support" in lower_path:
                system_id = "support_platform"
                category = "SUPPORT_ATTACHMENT"
            elif "security" in lower_path or "journal" in lower_path:
                system_id = "security_service"
                category = "SECURITY_AUDIT_LOG"
            elif "legal" in lower_path or "retention" in lower_path:
                system_id = "legal_service"
                category = "LEGAL_HOLD_RECORD"
            elif "account" in lower_path:
                system_id = "account_service"
                category = "USER_PROFILE"

            identifiers: Dict[str, str] = {}
            if emails:
                identifiers["email"] = next(iter(emails)).lower()
            if user_ids:
                identifiers["user_id"] = next(iter(user_ids))

            if resource_ids:
                for rid in resource_ids:
                    observations.append(
                        EvidenceObservation(
                            source_file=file_path,
                            evidence_id=evidence_id,
                            timestamp=file_ts,
                            system_id=system_id,
                            resource_id=rid,
                            data_category=category,
                            extracted_state="PRESENT",
                            identifiers=dict(identifiers),
                            raw_data={"pdf_pages": len(doc), "sample_text": full_text[:300]},
                            extraction_method="pdf_pymupdf_extracted",
                        )
                    )
            else:
                # If no explicit resource_id found, create one based on filename
                base_name = file_path.split("/")[-1].split("\\")[-1].replace(".pdf", "")
                observations.append(
                    EvidenceObservation(
                        source_file=file_path,
                        evidence_id=evidence_id,
                        timestamp=file_ts,
                        system_id=system_id,
                        resource_id=base_name,
                        data_category=category,
                        extracted_state="PRESENT",
                        identifiers=identifiers,
                        raw_data={"pdf_pages": len(doc), "sample_text": full_text[:300]},
                        extraction_method="pdf_pymupdf_extracted",
                    )
                )

        except Exception as e:
            self.log_warning(
                file_path=file_path,
                warning_type="PDF_PARSE_ERROR",
                message=str(e),
                file_id=evidence_id,
            )

        return observations
