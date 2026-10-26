"""Safe SQLite execution and table observation extraction for SQL snapshot files."""

from __future__ import annotations

from datetime import datetime
import json
import sqlite3
from typing import Any, Dict, List, Optional

from code.evidence.parsers.base import BaseEvidenceParser
from code.models import EvidenceManifestEntry, EvidenceObservation


class SQLEvidenceParser(BaseEvidenceParser):
    """Executes SQL files in in-memory SQLite and extracts structured observations."""

    def can_parse(self, file_path: str) -> bool:
        return file_path.lower().endswith(".sql")

    def parse(
        self,
        file_path: str,
        manifest_entry: Optional[EvidenceManifestEntry] = None,
    ) -> List[EvidenceObservation]:
        observations: List[EvidenceObservation] = []
        evidence_id = manifest_entry.file_id if manifest_entry else ""
        file_ts = manifest_entry.captured_at if manifest_entry else None

        conn: Optional[sqlite3.Connection] = None
        try:
            with open(file_path, mode="r", encoding="utf-8", errors="replace") as f:
                sql_script = f.read()

            conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row
            conn.executescript(sql_script)

            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            table_names = [row["name"] for row in cursor.fetchall()]

            # Category 1: Inventory tables (e.g., evidence_93 customer_data_inventory_*.sql)
            if "customer_profiles" in table_names or "customer_search_documents" in table_names:
                self._parse_inventory_tables(cursor, table_names, file_path, evidence_id, file_ts, observations)

            # Category 2: Primary vs Replica drift (e.g., customer_data_primary & customer_data_read_replica)
            elif "customer_data_primary" in table_names:
                self._parse_customer_data_replicas(cursor, table_names, file_path, evidence_id, file_ts, observations)

            # Category 3: Failover accounts replica (e.g., customer_profiles_primary & customer_profiles_failover_replica)
            elif "customer_profiles_primary" in table_names and "customer_profiles_failover_replica" in table_names:
                self._parse_account_failover_replica(cursor, file_path, evidence_id, file_ts, observations)

            # Category 4: Fallback for arbitrary tables
            else:
                self._parse_generic_tables(cursor, table_names, file_path, evidence_id, file_ts, observations)

        except Exception as e:
            self.log_warning(
                file_path=file_path,
                warning_type="SQL_EXECUTION_ERROR",
                message=str(e),
                file_id=evidence_id,
            )
        finally:
            if conn:
                conn.close()

        return observations

    def _parse_inventory_tables(
        self,
        cursor: sqlite3.Cursor,
        table_names: List[str],
        file_path: str,
        evidence_id: str,
        file_ts: Optional[datetime],
        observations: List[EvidenceObservation],
    ) -> None:
        """Parse tables from customer_data_inventory captures."""
        # 1. customer_profiles
        if "customer_profiles" in table_names:
            cursor.execute("SELECT * FROM customer_profiles")
            for row in cursor.fetchall():
                r = dict(row)
                res_id = r.get("resource_id", "")
                ts = self._parse_iso_ts(r.get("updated_at")) or file_ts
                status = r.get("account_status", "ACTIVE")
                ident = self._extract_identifiers(r)
                state = "PRESENT" if status == "ACTIVE" else "ABSENT"
                observations.append(
                    EvidenceObservation(
                        source_file=file_path,
                        evidence_id=evidence_id,
                        timestamp=ts,
                        system_id="account_service",
                        resource_id=res_id,
                        data_category="customer_profiles",
                        extracted_state=state,
                        identifiers=ident,
                        raw_data=r,
                        extraction_method="sql_table_inventory",
                    )
                )

        # 2. customer_search_documents
        if "customer_search_documents" in table_names:
            cursor.execute("SELECT * FROM customer_search_documents")
            for row in cursor.fetchall():
                r = dict(row)
                res_id = r.get("resource_id", "")
                ts = self._parse_iso_ts(r.get("updated_at")) or file_ts
                ident = self._extract_identifiers(r)
                observations.append(
                    EvidenceObservation(
                        source_file=file_path,
                        evidence_id=evidence_id,
                        timestamp=ts,
                        system_id="search_service",
                        resource_id=res_id,
                        data_category="customer_search_documents",
                        extracted_state="PRESENT",
                        identifiers=ident,
                        raw_data=r,
                        extraction_method="sql_table_inventory",
                    )
                )

        # 3. customer_analytics_profiles
        if "customer_analytics_profiles" in table_names:
            cursor.execute("SELECT * FROM customer_analytics_profiles")
            for row in cursor.fetchall():
                r = dict(row)
                res_id = r.get("resource_id", "")
                ts = self._parse_iso_ts(r.get("updated_at")) or file_ts
                ident = self._extract_identifiers(r)
                has_ident = any(ident.get(k) for k in ["email", "phone", "email_hash"])
                state = "PRESENT" if has_ident else "ANONYMIZED"
                observations.append(
                    EvidenceObservation(
                        source_file=file_path,
                        evidence_id=evidence_id,
                        timestamp=ts,
                        system_id="analytics_platform",
                        resource_id=res_id,
                        data_category="customer_analytics_profiles",
                        extracted_state=state,
                        identifiers=ident,
                        raw_data=r,
                        extraction_method="sql_table_inventory",
                    )
                )

        # 4. support_records
        if "support_records" in table_names:
            cursor.execute("SELECT * FROM support_records")
            for row in cursor.fetchall():
                r = dict(row)
                res_id = r.get("resource_id", "")
                ts = self._parse_iso_ts(r.get("updated_at")) or file_ts
                ident = self._extract_identifiers(r)
                has_pii = any(r.get(k) for k in ["requester_name", "requester_email", "requester_phone"])
                state = "PRESENT" if has_pii else "REDACTED"
                observations.append(
                    EvidenceObservation(
                        source_file=file_path,
                        evidence_id=evidence_id,
                        timestamp=ts,
                        system_id="support_platform",
                        resource_id=res_id,
                        data_category="support_records",
                        extracted_state=state,
                        identifiers=ident,
                        raw_data=r,
                        extraction_method="sql_table_inventory",
                    )
                )

        # 5. connector_subscriptions
        if "connector_subscriptions" in table_names:
            cursor.execute("SELECT * FROM connector_subscriptions")
            for row in cursor.fetchall():
                r = dict(row)
                res_id = r.get("resource_id", "")
                ts = self._parse_iso_ts(r.get("updated_at")) or file_ts
                ident = self._extract_identifiers(r)
                enabled = bool(r.get("enabled", 0))
                state = "ACTIVE" if enabled else "DISABLED"
                observations.append(
                    EvidenceObservation(
                        source_file=file_path,
                        evidence_id=evidence_id,
                        timestamp=ts,
                        system_id="integration_service",
                        resource_id=res_id,
                        data_category="connector_subscriptions",
                        extracted_state=state,
                        identifiers=ident,
                        raw_data=r,
                        extraction_method="sql_table_inventory",
                    )
                )

        # 6. backup_restore_entries
        if "backup_restore_entries" in table_names:
            cursor.execute("SELECT * FROM backup_restore_entries")
            for row in cursor.fetchall():
                r = dict(row)
                res_id = r.get("resource_id", "")
                ts = self._parse_iso_ts(r.get("updated_at")) or file_ts
                ident = self._extract_identifiers(r)
                restore_allowed = bool(r.get("restore_allowed", 0))
                state = "ACTIVE" if restore_allowed else "BLOCKED"
                observations.append(
                    EvidenceObservation(
                        source_file=file_path,
                        evidence_id=evidence_id,
                        timestamp=ts,
                        system_id="backup_service",
                        resource_id=res_id,
                        data_category="backup_restore_entries",
                        extracted_state=state,
                        identifiers=ident,
                        raw_data=r,
                        extraction_method="sql_table_inventory",
                    )
                )

        # 7. security_audit_records
        if "security_audit_records" in table_names:
            cursor.execute("SELECT * FROM security_audit_records")
            for row in cursor.fetchall():
                r = dict(row)
                res_id = r.get("resource_id", "")
                ts = self._parse_iso_ts(r.get("updated_at")) or file_ts
                ident = self._extract_identifiers(r)
                observations.append(
                    EvidenceObservation(
                        source_file=file_path,
                        evidence_id=evidence_id,
                        timestamp=ts,
                        system_id="security_service",
                        resource_id=res_id,
                        data_category="security_audit_records",
                        extracted_state="PRESENT",
                        identifiers=ident,
                        raw_data=r,
                        extraction_method="sql_table_inventory",
                    )
                )

    def _parse_customer_data_replicas(
        self,
        cursor: sqlite3.Cursor,
        table_names: List[str],
        file_path: str,
        evidence_id: str,
        file_ts: Optional[datetime],
        observations: List[EvidenceObservation],
    ) -> None:
        """Parse primary and replica tables storing JSON records."""
        # Find replica table name
        replica_tables = [t for t in table_names if t != "customer_data_primary" and "replica" in t]
        target_replica = replica_tables[0] if replica_tables else "customer_data_primary"

        cursor.execute(f"SELECT * FROM {target_replica}")
        for row in cursor.fetchall():
            r = dict(row)
            res_id = r.get("resource_id", "")
            origin_sys = r.get("origin_system", "system")
            rec_json_str = r.get("record_json", "{}")
            rec_json = {}
            try:
                rec_json = json.loads(rec_json_str)
            except Exception:
                pass

            ident = self._extract_identifiers(rec_json)
            ts = self._parse_iso_ts(r.get("updated_at")) or file_ts

            # Determine state from embedded record
            state = "PRESENT"
            if origin_sys == "analytics_platform":
                has_ident = any(ident.get(k) for k in ["email", "phone", "email_hash"])
                state = "PRESENT" if has_ident else "ANONYMIZED"

            observations.append(
                EvidenceObservation(
                    source_file=file_path,
                    evidence_id=evidence_id,
                    timestamp=ts,
                    system_id=origin_sys,
                    resource_id=res_id,
                    data_category=r.get("collection_name"),
                    extracted_state=state,
                    identifiers=ident,
                    raw_data=rec_json,
                    extraction_method="sql_replica_drift",
                )
            )

    def _parse_account_failover_replica(
        self,
        cursor: sqlite3.Cursor,
        file_path: str,
        evidence_id: str,
        file_ts: Optional[datetime],
        observations: List[EvidenceObservation],
    ) -> None:
        """Parse failover replica accounts table to detect replication drift."""
        cursor.execute("SELECT * FROM customer_profiles_failover_replica")
        for row in cursor.fetchall():
            r = dict(row)
            res_id = r.get("resource_id", "")
            ts = self._parse_iso_ts(r.get("updated_at")) or file_ts
            ident = self._extract_identifiers(r)
            status = r.get("account_status", "ACTIVE")
            state = "PRESENT" if status == "ACTIVE" else "ABSENT"

            observations.append(
                EvidenceObservation(
                    source_file=file_path,
                    evidence_id=evidence_id,
                    timestamp=ts,
                    system_id="account_service",
                    resource_id=res_id,
                    data_category="customer_profiles",
                    extracted_state=state,
                    identifiers=ident,
                    raw_data=r,
                    extraction_method="sql_account_failover_replica",
                )
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

    def _parse_generic_tables(
        self,
        cursor: sqlite3.Cursor,
        table_names: List[str],
        file_path: str,
        evidence_id: str,
        file_ts: Optional[datetime],
        observations: List[EvidenceObservation],
    ) -> None:
        """Fallback extractor for unexpected tables."""
        for t in table_names:
            cursor.execute(f"SELECT * FROM {t}")
            for row in cursor.fetchall():
                r = dict(row)
                res_id = r.get("resource_id") or r.get("id") or f"{t}_row"
                ident = self._extract_identifiers(r)
                observations.append(
                    EvidenceObservation(
                        source_file=file_path,
                        evidence_id=evidence_id,
                        timestamp=file_ts,
                        system_id=self._normalize_system_id(t),
                        resource_id=res_id,
                        data_category=t,
                        extracted_state="PRESENT",
                        identifiers=ident,
                        raw_data=r,
                        extraction_method="sql_generic_table",
                    )
                )

    @staticmethod
    def _extract_identifiers(data: Dict[str, Any]) -> Dict[str, str]:
        ident: Dict[str, str] = {}

        def _search(d: Any) -> None:
            if isinstance(d, dict):
                for k, v in d.items():
                    k_lower = k.lower()
                    if v and any(term in k_lower for term in ["email", "user", "phone", "hash", "customer_reference", "subject_reference"]):
                        if isinstance(v, (str, int)):
                            ident[k] = str(v)
                    _search(v)
            elif isinstance(d, list):
                for item in d:
                    _search(item)

        _search(data)
        return ident

    @staticmethod
    def _parse_iso_ts(ts_str: Any) -> Optional[datetime]:
        if not ts_str or not isinstance(ts_str, str):
            return None
        try:
            return datetime.fromisoformat(ts_str.strip().replace("Z", "+00:00"))
        except Exception:
            return None
