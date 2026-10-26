"""JSON and JSONL parser for service exports, snapshot bundles, and manifests."""

from __future__ import annotations

from datetime import datetime
import json
from typing import Any, Dict, List, Optional

from code.evidence.parsers.base import BaseEvidenceParser
from code.models import EvidenceManifestEntry, EvidenceObservation


class JSONEvidenceParser(BaseEvidenceParser):
    """Parses JSON and JSONL evidence files into EvidenceObservations."""

    def can_parse(self, file_path: str) -> bool:
        lower = file_path.lower()
        return lower.endswith(".json") or lower.endswith(".jsonl")

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
                content = f.read().strip()
                if not content:
                    return observations

                # Handle JSONL
                if file_path.lower().endswith(".jsonl"):
                    for line_idx, line in enumerate(content.splitlines()):
                        if not line.strip():
                            continue
                        try:
                            record = json.loads(line)
                            obs = self._parse_generic_record(record, file_path, evidence_id, file_ts, f"line_{line_idx}")
                            if obs:
                                observations.append(obs)
                        except Exception as e:
                            self.log_warning(file_path, "JSONL_LINE_ERROR", f"Line {line_idx}: {e}", evidence_id)
                    return observations

                # Standard JSON
                data = json.loads(content)

            # Case 1: Service resource export bundle (e.g., evidence_92)
            if isinstance(data, dict) and "service_exports" in data:
                exported_at_str = data.get("exported_at")
                bundle_ts = self._parse_iso_ts(exported_at_str) or file_ts

                for service_name, export_content in data["service_exports"].items():
                    if isinstance(export_content, dict):
                        for category_key, records_list in export_content.items():
                            if isinstance(records_list, list):
                                for item in records_list:
                                    if isinstance(item, dict):
                                        obs = self._parse_service_export_item(
                                            item, service_name, category_key, file_path, evidence_id, bundle_ts
                                        )
                                        if obs:
                                            observations.append(obs)

            # Case 2: Customer data snapshot bundle (e.g., evidence_51)
            elif isinstance(data, dict) and "snapshots" in data:
                exported_at_str = data.get("exported_at")
                bundle_ts = self._parse_iso_ts(exported_at_str) or file_ts

                snapshots = data.get("snapshots", [])
                if isinstance(snapshots, list):
                    for snapshot in snapshots:
                        if isinstance(snapshot, dict):
                            data_store = snapshot.get("data_store", "data_store")
                            collection = snapshot.get("collection", "records")
                            snap_ts = self._parse_iso_ts(snapshot.get("captured_at")) or bundle_ts
                            for rec in snapshot.get("records", []):
                                if isinstance(rec, dict):
                                    obs = self._parse_snapshot_record(
                                        rec, data_store, collection, file_path, evidence_id, snap_ts
                                    )
                                    if obs:
                                        observations.append(obs)

            # Case 3: Flat records list (e.g. connector_configurations, export_jobs, analytics_report)
            elif isinstance(data, dict) and "records" in data:
                source = data.get("source") or data.get("origin") or "system"
                coll = data.get("collection") or "records"
                doc_ts = self._parse_iso_ts(data.get("captured_at") or data.get("exported_at")) or file_ts
                for rec in data.get("records", []):
                    if isinstance(rec, dict):
                        obs = self._parse_generic_record(rec, file_path, evidence_id, doc_ts, default_sys=source)
                        if obs:
                            observations.append(obs)

            # Case 4: Top-level list of dicts
            elif isinstance(data, list):
                for idx, item in enumerate(data):
                    if isinstance(item, dict):
                        obs = self._parse_generic_record(item, file_path, evidence_id, file_ts, f"rec_{idx}")
                        if obs:
                            observations.append(obs)

        except Exception as e:
            self.log_warning(
                file_path=file_path,
                warning_type="JSON_PARSE_ERROR",
                message=str(e),
                file_id=evidence_id,
            )

        return observations

    def _parse_service_export_item(
        self,
        item: Dict[str, Any],
        service_name: str,
        category_key: str,
        file_path: str,
        evidence_id: str,
        default_ts: Optional[datetime],
    ) -> Optional[EvidenceObservation]:
        res_id = item.get("resource_id") or ""
        ts = self._parse_iso_ts(item.get("observed_at")) or default_ts
        identifiers: Dict[str, str] = {}

        # Default extracted state
        state = "PRESENT"

        # Check account service profile lookups
        if service_name == "account_service":
            status_code = item.get("status_code")
            if status_code == 404:
                state = "ABSENT"
            profile = item.get("profile") or {}
            if isinstance(profile, dict):
                for k in ["email", "user_id", "customer_reference", "phone", "email_hash"]:
                    if profile.get(k):
                        identifiers[k] = str(profile[k])

        # Check search service index queries
        elif service_name == "search_service":
            hits = item.get("hits") or {}
            total = hits.get("total", 0) if isinstance(hits, dict) else 0
            if total == 0:
                state = "ABSENT"
            query = item.get("query")
            if query and "@" in str(query):
                identifiers["email"] = str(query).lower()
            if isinstance(hits, dict):
                for doc in hits.get("documents", []):
                    for k in ["email", "customer_reference", "phone", "email_hash"]:
                        if doc.get(k):
                            identifiers[k] = str(doc[k])

        # Check analytics platform profiles
        elif service_name == "analytics_platform":
            has_ident = False
            for k in ["email", "phone", "email_hash", "customer_reference", "user_id"]:
                val = item.get(k)
                if val:
                    identifiers[k] = str(val)
                    has_ident = True
            if not has_ident:
                state = "ANONYMIZED"

        # Check integration service connectors
        elif service_name == "integration_service":
            enabled = item.get("enabled")
            state = "ACTIVE" if enabled is True else "DISABLED"
            for k in ["customer_email", "customer_reference"]:
                if item.get(k):
                    identifiers[k] = str(item[k])

        # Check backup service restore entries
        elif service_name == "backup_service":
            restore_allowed = item.get("restore_allowed")
            state = "ACTIVE" if restore_allowed is True else "BLOCKED"
            for k in ["customer_email", "customer_reference"]:
                if item.get(k):
                    identifiers[k] = str(item[k])

        # Check support tickets
        elif service_name == "support_platform":
            has_ident = False
            for k in ["requester_email", "requester_phone", "requester_name", "customer_reference"]:
                val = item.get(k)
                if val:
                    identifiers[k] = str(val)
                    if k in {"requester_email", "requester_phone", "requester_name"}:
                        has_ident = True
            if not has_ident and item.get("customer_reference"):
                state = "REDACTED"

        # Check security audit records
        elif service_name == "security_service":
            state = "PRESENT"
            for k in ["subject_reference", "user_id"]:
                if item.get(k):
                    identifiers[k] = str(item[k])

        # Check export service
        elif service_name == "export_service":
            state = "PRESENT"
            for k in ["owner_email", "owner_phone", "customer_reference"]:
                if item.get(k):
                    identifiers[k] = str(item[k])

        return EvidenceObservation(
            source_file=file_path,
            evidence_id=evidence_id,
            timestamp=ts,
            system_id=service_name,
            resource_id=res_id,
            data_category=category_key,
            extracted_state=state,
            identifiers=identifiers,
            raw_data=item,
            extraction_method="json_service_export",
        )

    def _parse_snapshot_record(
        self,
        rec: Dict[str, Any],
        data_store: str,
        collection: str,
        file_path: str,
        evidence_id: str,
        timestamp: Optional[datetime],
    ) -> Optional[EvidenceObservation]:
        res_id = rec.get("resource_id") or ""
        identifiers: Dict[str, str] = {}
        for k in ["user_id", "subject_reference", "customer_reference", "email", "phone", "email_hash", "name"]:
            if rec.get(k):
                identifiers[k] = str(rec[k])

        # Determine state
        state = "PRESENT"
        if data_store == "identity_service" and collection == "deleted_customer_references":
            # Check if direct PII is exposed
            direct_pii = any(rec.get(k) for k in ["email", "phone", "email_hash", "name"])
            state = "PRESENT" if direct_pii else "REDACTED"
        elif rec.get("account_status") == "DELETED" and not any(rec.get(k) for k in ["email", "phone"]):
            state = "REDACTED"
        elif rec.get("account_status") == "ACTIVE":
            state = "PRESENT"

        return EvidenceObservation(
            source_file=file_path,
            evidence_id=evidence_id,
            timestamp=timestamp,
            system_id=data_store,
            resource_id=res_id,
            data_category=collection,
            extracted_state=state,
            identifiers=identifiers,
            raw_data=rec,
            extraction_method="json_snapshot_record",
        )

    @staticmethod
    def _normalize_system_id(sys_str: str) -> str:
        if not sys_str:
            return "system"
        s = sys_str.lower()
        if "support" in s:
            return "support_platform"
        if "analytics" in s or "telemetry" in s:
            return "analytics_platform"
        if "search" in s:
            return "search_service"
        if "account" in s or "profile" in s:
            return "account_service"
        if "integration" in s or "connector" in s:
            return "integration_service"
        if "backup" in s or "restore" in s:
            return "backup_service"
        if "security" in s or "audit" in s:
            return "security_service"
        if "export" in s:
            return "export_service"
        if "identity" in s or "tombstone" in s:
            return "identity_service"
        return sys_str

    def _parse_generic_record(
        self,
        rec: Dict[str, Any],
        file_path: str,
        evidence_id: str,
        timestamp: Optional[datetime],
        fallback_id: str = "rec",
        default_sys: str = "generic_json",
    ) -> Optional[EvidenceObservation]:
        res_id = rec.get("resource_id") or rec.get("id") or fallback_id
        sys_id = self._normalize_system_id(rec.get("system_id") or rec.get("service") or default_sys)
        state = rec.get("state") or rec.get("status") or "PRESENT"

        identifiers: Dict[str, str] = {}
        for k, v in rec.items():
            if v and any(term in k.lower() for term in ["email", "user", "phone", "hash", "reference"]):
                clean_v = str(v).strip()
                if "@" in clean_v or "email" in k.lower():
                    identifiers["email"] = clean_v.lower()
                elif clean_v.startswith("user_"):
                    identifiers["user_id"] = clean_v
                else:
                    identifiers[k] = clean_v

        return EvidenceObservation(
            source_file=file_path,
            evidence_id=evidence_id,
            timestamp=timestamp,
            system_id=sys_id,
            resource_id=res_id,
            data_category=rec.get("category"),
            extracted_state=str(state).upper(),
            identifiers=identifiers,
            raw_data=rec,
            extraction_method="json_generic_record",
        )

    @staticmethod
    def _parse_iso_ts(ts_str: Any) -> Optional[datetime]:
        if not ts_str or not isinstance(ts_str, str):
            return None
        try:
            return datetime.fromisoformat(ts_str.strip().replace("Z", "+00:00"))
        except Exception:
            return None
