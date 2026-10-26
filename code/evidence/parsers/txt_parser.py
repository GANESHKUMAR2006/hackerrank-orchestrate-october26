"""Plain text and pipe-delimited record parser (e.g. shift handover logs)."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from code.evidence.parsers.base import BaseEvidenceParser
from code.models import EvidenceManifestEntry, EvidenceObservation


class TextEvidenceParser(BaseEvidenceParser):
    """Parses pipe-delimited text files (e.g., customer_account_handover_*.txt)."""

    def can_parse(self, file_path: str) -> bool:
        return file_path.lower().endswith(".txt")

    def parse(
        self,
        file_path: str,
        manifest_entry: Optional[EvidenceManifestEntry] = None,
    ) -> List[EvidenceObservation]:
        observations: List[EvidenceObservation] = []
        evidence_id = manifest_entry.file_id if manifest_entry else ""
        file_ts = manifest_entry.captured_at if manifest_entry else None

        try:
            with open(file_path, mode="r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            for line_idx, line in enumerate(lines):
                line = line.strip()
                if not line or not line.startswith("-"):
                    continue

                # Strip leading '- '
                parts = [p.strip() for p in line.lstrip("-").split("|")]
                if len(parts) >= 5:
                    ts_str = parts[0]
                    system_id = parts[1]
                    resource_id = parts[2]
                    category = parts[3]
                    status = parts[4].upper()
                    ident_str = parts[5] if len(parts) > 5 else ""

                    ts = self._parse_iso_ts(ts_str) or file_ts

                    # Map status string to normalized State enum
                    if status == "NOT_FOUND":
                        state = "ABSENT"
                    elif status in {"FOUND", "IDENTIFIABLE"}:
                        state = "PRESENT"
                    elif status == "ACTIVE":
                        state = "ACTIVE"
                    elif status == "DISABLED":
                        state = "DISABLED"
                    elif status == "BLOCKED":
                        state = "BLOCKED"
                    elif status == "ANONYMIZED":
                        state = "ANONYMIZED"
                    elif status == "REDACTED":
                        state = "REDACTED"
                    else:
                        state = status

                    identifiers: Dict[str, str] = {}
                    if "@" in ident_str:
                        identifiers["email"] = ident_str.lower()
                    elif ident_str.startswith("user_"):
                        identifiers["user_id"] = ident_str
                    elif ident_str and ident_str != "no direct identifier":
                        identifiers["reference"] = ident_str

                    observations.append(
                        EvidenceObservation(
                            source_file=file_path,
                            evidence_id=evidence_id,
                            timestamp=ts,
                            system_id=system_id,
                            resource_id=resource_id,
                            data_category=category,
                            extracted_state=state,
                            identifiers=identifiers,
                            raw_data={"raw_line": line, "status": status},
                            extraction_method="txt_pipe_delimited",
                        )
                    )

        except Exception as e:
            self.log_warning(
                file_path=file_path,
                warning_type="TXT_PARSE_ERROR",
                message=str(e),
                file_id=evidence_id,
            )

        return observations

    @staticmethod
    def _parse_iso_ts(ts_str: Any) -> Optional[datetime]:
        if not ts_str or not isinstance(ts_str, str):
            return None
        try:
            return datetime.fromisoformat(ts_str.strip().replace("Z", "+00:00"))
        except Exception:
            return None
