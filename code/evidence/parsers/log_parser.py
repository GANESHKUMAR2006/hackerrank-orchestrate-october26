"""Log parser for structured service logs, trace events, and readback streams."""

from __future__ import annotations

from datetime import datetime
import json
import re
from typing import Any, Dict, List, Optional

from code.evidence.parsers.base import BaseEvidenceParser
from code.models import EvidenceManifestEntry, EvidenceObservation


class LogEvidenceParser(BaseEvidenceParser):
    """Parses .log files, extracting observations from key-value pairs and trace groups."""

    # Matches key=value or key="value with spaces"
    KV_REGEX = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)=(?:"([^"]*)"|([^\s]+))')
    ISO_DATE_REGEX = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)")

    def can_parse(self, file_path: str) -> bool:
        return file_path.lower().endswith(".log")

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

            # Pass 1: Parse key-values and group by trace_id if available
            trace_groups: Dict[str, Dict[str, Any]] = {}
            untraced_records: List[Dict[str, Any]] = []

            for line_idx, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue

                ts_match = self.ISO_DATE_REGEX.match(line)
                line_ts = self._parse_iso_ts(ts_match.group(1)) if ts_match else file_ts

                kvs: Dict[str, str] = {}
                # Handle embedded JSON payloads in log lines (e.g. structured_service_events_*.log)
                if "{" in line and "}" in line:
                    json_str = line[line.find("{"):line.rfind("}") + 1]
                    try:
                        parsed_json = json.loads(json_str)
                        if isinstance(parsed_json, dict):
                            for jk, jv in parsed_json.items():
                                if jv is not None:
                                    kvs[str(jk)] = str(jv)
                    except Exception:
                        pass

                for match in self.KV_REGEX.finditer(line):
                    k = match.group(1)
                    v = match.group(2) if match.group(2) is not None else match.group(3)
                    kvs[k] = v

                # Also extract bracketed tags e.g. [DEBUG] [account_service] [tr-123]
                brackets = re.findall(r"\[([a-zA-Z0-9_\-\.:@]+)\]", line)
                for b in brackets:
                    if "@" in b:
                        kvs.setdefault("email", b)
                    elif b.startswith("tr-") or b.startswith("rb-"):
                        kvs.setdefault("trace_id", b)
                    elif b.endswith("_service") or b in {"support_platform", "analytics_platform", "identity_service"}:
                        kvs.setdefault("service", b)

                trace_id = kvs.get("trace_id")
                if trace_id:
                    if trace_id not in trace_groups:
                        trace_groups[trace_id] = {"timestamp": line_ts, "data": {}}
                    trace_groups[trace_id]["data"].update(kvs)
                    if line_ts and not trace_groups[trace_id]["timestamp"]:
                        trace_groups[trace_id]["timestamp"] = line_ts
                else:
                    untraced_records.append({"timestamp": line_ts, "data": kvs, "raw_line": line})

            # Process trace groups
            for trace_id, group in trace_groups.items():
                data = group["data"]
                res_id = data.get("resource_id")
                if res_id:
                    obs = self._build_observation(
                        data=data,
                        res_id=res_id,
                        file_path=file_path,
                        evidence_id=evidence_id,
                        timestamp=group["timestamp"] or file_ts,
                    )
                    if obs:
                        observations.append(obs)

            # Process untraced lines with resource_id
            for rec in untraced_records:
                data = rec["data"]
                res_id = data.get("resource_id")
                if res_id:
                    obs = self._build_observation(
                        data=data,
                        res_id=res_id,
                        file_path=file_path,
                        evidence_id=evidence_id,
                        timestamp=rec["timestamp"] or file_ts,
                    )
                    if obs:
                        observations.append(obs)

        except Exception as e:
            self.log_warning(
                file_path=file_path,
                warning_type="LOG_PARSE_ERROR",
                message=str(e),
                file_id=evidence_id,
            )

        return observations

    def _build_observation(
        self,
        data: Dict[str, Any],
        res_id: str,
        file_path: str,
        evidence_id: str,
        timestamp: Optional[datetime],
    ) -> Optional[EvidenceObservation]:
        # Normalize system_id
        service = data.get("service") or data.get("system") or data.get("source") or "system"
        if "support" in service:
            system_id = "support_platform"
        elif "analytics" in service:
            system_id = "analytics_platform"
        elif "search" in service:
            system_id = "search_service"
        elif "account" in service:
            system_id = "account_service"
        elif "integration" in service or "connector" in service:
            system_id = "integration_service"
        elif "backup" in service or "restore" in service:
            system_id = "backup_service"
        elif "security" in service or "audit" in service:
            system_id = "security_service"
        elif "export" in service:
            system_id = "export_service"
        elif "identity" in service:
            system_id = "identity_service"
        else:
            system_id = service

        # Extract identifiers
        ident: Dict[str, str] = {}
        for k, val in data.items():
            if val and val != "null":
                clean_val = str(val).strip()
                if "@" in clean_val:
                    ident["email"] = clean_val.lower()
                elif clean_val.startswith("user_"):
                    ident["user_id"] = clean_val
                elif len(clean_val) == 64 and all(c in "0123456789abcdefABCDEF" for c in clean_val):
                    ident["email_hash"] = clean_val.lower()
                elif k in {"phone", "correlation_key", "customer_reference", "subject_reference", "subject_ref"}:
                    ident[k] = clean_val

        # Determine extracted state
        state = "PRESENT"
        http_status = data.get("http_status")
        rows = data.get("rows")
        result = data.get("result")
        enabled = data.get("enabled")
        restore_allowed = data.get("restore_allowed")

        if http_status == "404" or rows == "0" or result == "miss":
            state = "ABSENT"
        elif enabled == "false" or data.get("status") == "stopped":
            state = "DISABLED"
        elif enabled == "true":
            state = "ACTIVE"
        elif restore_allowed == "false" or data.get("deletion_block") == "true":
            state = "BLOCKED"
        elif restore_allowed == "true" or data.get("deletion_block") == "false":
            state = "ACTIVE"
        elif system_id == "analytics_platform":
            has_direct_pii = any(ident.get(k) for k in ["email", "phone", "email_hash"])
            state = "PRESENT" if has_direct_pii else "ANONYMIZED"
        elif system_id == "support_platform":
            has_direct_pii = any(ident.get(k) for k in ["email", "phone"])
            state = "PRESENT" if has_direct_pii else "REDACTED"

        return EvidenceObservation(
            source_file=file_path,
            evidence_id=evidence_id,
            timestamp=timestamp,
            system_id=system_id,
            resource_id=res_id,
            data_category=data.get("event") or data.get("event_type"),
            extracted_state=state,
            identifiers=ident,
            raw_data=data,
            extraction_method="log_kv_trace",
        )

    @staticmethod
    def _parse_iso_ts(ts_str: Any) -> Optional[datetime]:
        if not ts_str or not isinstance(ts_str, str):
            return None
        try:
            return datetime.fromisoformat(ts_str.strip().replace("Z", "+00:00"))
        except Exception:
            return None
