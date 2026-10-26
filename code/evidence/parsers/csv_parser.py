"""CSV parsers for structured datasets and activity logs."""

from __future__ import annotations

import csv
from typing import Dict, List, Optional

from code.evidence.parsers.base import BaseEvidenceParser
from code.models import (
    DeletionRequest,
    EvidenceManifestEntry,
    EvidenceObservation,
    PolicyRule,
    SystemActivity,
    UserAuditEntry,
    UserIdentity,
)


class CSVDatasetParser(BaseEvidenceParser):
    """Parses standard CSV dataset files."""

    def can_parse(self, file_path: str) -> bool:
        return file_path.lower().endswith(".csv")

    def parse(
        self,
        file_path: str,
        manifest_entry: Optional[EvidenceManifestEntry] = None,
    ) -> List[EvidenceObservation]:
        """Generic CSV parser to observations."""
        observations: List[EvidenceObservation] = []
        try:
            with open(file_path, mode="r", encoding="utf-8-sig", errors="replace") as f:
                reader = csv.DictReader(f)
                for idx, raw_row in enumerate(reader):
                    row = {k.lstrip("\ufeff").strip(): (v.strip() if v else "") for k, v in raw_row.items() if k}
                    res_id = row.get("resource_id") or row.get("case_id") or f"row_{idx}"
                    sys_id = row.get("system_id") or row.get("source_system") or "csv_store"
                    observations.append(
                        EvidenceObservation(
                            source_file=file_path,
                            evidence_id=manifest_entry.file_id if manifest_entry else "",
                            timestamp=manifest_entry.captured_at if manifest_entry else None,
                            system_id=sys_id,
                            resource_id=res_id,
                            data_category=row.get("data_category"),
                            extracted_state=row.get("state") or row.get("reported_result") or "PRESENT",
                            identifiers={k: v for k, v in row.items() if k in {"email", "user_id", "phone", "email_hash"}},
                            raw_data=dict(row),
                            extraction_method="csv_row",
                        )
                    )
        except Exception as e:
            self.log_warning(
                file_path=file_path,
                warning_type="CSV_READ_ERROR",
                message=str(e),
                file_id=manifest_entry.file_id if manifest_entry else None,
            )
        return observations

    @staticmethod
    def parse_deletion_requests(file_path: str) -> List[DeletionRequest]:
        requests: List[DeletionRequest] = []
        with open(file_path, mode="r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for raw_row in reader:
                row = {k.lstrip("\ufeff").strip(): v for k, v in raw_row.items() if k}
                requests.append(DeletionRequest.from_row(row))
        return requests

    @staticmethod
    def parse_user_identities(file_path: str) -> List[UserIdentity]:
        identities: List[UserIdentity] = []
        with open(file_path, mode="r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for raw_row in reader:
                row = {k.lstrip("\ufeff").strip(): v for k, v in raw_row.items() if k}
                identities.append(UserIdentity.from_row(row))
        return identities

    @staticmethod
    def parse_user_audit_log(file_path: str) -> List[UserAuditEntry]:
        entries: List[UserAuditEntry] = []
        with open(file_path, mode="r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for raw_row in reader:
                row = {k.lstrip("\ufeff").strip(): v for k, v in raw_row.items() if k}
                entries.append(UserAuditEntry.from_row(row))
        return entries

    @staticmethod
    def parse_policy_rules(file_path: str) -> List[PolicyRule]:
        rules: List[PolicyRule] = []
        with open(file_path, mode="r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for raw_row in reader:
                row = {k.lstrip("\ufeff").strip(): v for k, v in raw_row.items() if k}
                rules.append(PolicyRule.from_row(row))
        return rules

    @staticmethod
    def parse_system_activities(file_path: str) -> List[SystemActivity]:
        activities: List[SystemActivity] = []
        with open(file_path, mode="r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for raw_row in reader:
                row = {k.lstrip("\ufeff").strip(): v for k, v in raw_row.items() if k}
                activities.append(SystemActivity.from_row(row))
        return activities

    @staticmethod
    def parse_evidence_manifest(file_path: str) -> List[EvidenceManifestEntry]:
        manifest: List[EvidenceManifestEntry] = []
        with open(file_path, mode="r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for raw_row in reader:
                row = {k.lstrip("\ufeff").strip(): v for k, v in raw_row.items() if k}
                manifest.append(EvidenceManifestEntry.from_row(row))
        return manifest
