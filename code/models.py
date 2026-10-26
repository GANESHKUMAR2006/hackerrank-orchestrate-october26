"""Core data models for Ghost Data Still Exists deletion audit agent.

This module defines typed representations for requests, user identity graphs,
evidence observations, policy rules, and final audit steps.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import json


class Phase(str, Enum):
    FINDING = "FINDING"
    REMEDIATION = "REMEDIATION"
    VERIFICATION = "VERIFICATION"


class Operation(str, Enum):
    # Finding operations
    REPORT_REMAINING_RECORD = "REPORT_REMAINING_RECORD"
    REPORT_EXPOSED_PII = "REPORT_EXPOSED_PII"
    REPORT_ACTIVE_DATA_FLOW = "REPORT_ACTIVE_DATA_FLOW"
    REPORT_RESTORE_RISK = "REPORT_RESTORE_RISK"

    # Remediation operations
    DISABLE_DATA_FLOW = "DISABLE_DATA_FLOW"
    BLOCK_RESTORE = "BLOCK_RESTORE"
    DELETE_RECORD = "DELETE_RECORD"
    REDACT_RECORD = "REDACT_RECORD"
    ANONYMIZE_RECORD = "ANONYMIZE_RECORD"

    # Verification operations
    VERIFY_RECORD_ABSENT = "VERIFY_RECORD_ABSENT"
    VERIFY_RECORD_PRESENT = "VERIFY_RECORD_PRESENT"
    VERIFY_RECORD_REDACTED = "VERIFY_RECORD_REDACTED"
    VERIFY_RECORD_ANONYMIZED = "VERIFY_RECORD_ANONYMIZED"
    VERIFY_DATA_FLOW_DISABLED = "VERIFY_DATA_FLOW_DISABLED"
    VERIFY_RESTORE_BLOCKED = "VERIFY_RESTORE_BLOCKED"


class State(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    BLOCKED = "BLOCKED"
    REDACTED = "REDACTED"
    ANONYMIZED = "ANONYMIZED"


class DeletionStatus(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


# Enforce the strict 5-level hierarchy operation order
OPERATION_PRECEDENCE: Dict[Phase, List[Operation]] = {
    Phase.FINDING: [
        Operation.REPORT_REMAINING_RECORD,
        Operation.REPORT_EXPOSED_PII,
        Operation.REPORT_ACTIVE_DATA_FLOW,
        Operation.REPORT_RESTORE_RISK,
    ],
    Phase.REMEDIATION: [
        Operation.DISABLE_DATA_FLOW,
        Operation.BLOCK_RESTORE,
        Operation.DELETE_RECORD,
        Operation.REDACT_RECORD,
        Operation.ANONYMIZE_RECORD,
    ],
    Phase.VERIFICATION: [
        Operation.VERIFY_RECORD_ABSENT,
        Operation.VERIFY_RECORD_PRESENT,
        Operation.VERIFY_RECORD_REDACTED,
        Operation.VERIFY_RECORD_ANONYMIZED,
        Operation.VERIFY_DATA_FLOW_DISABLED,
        Operation.VERIFY_RESTORE_BLOCKED,
    ],
}


@dataclass
class DeletionRequest:
    """Represents a deletion request row from dataset/deletion_requests.csv."""
    case_id: str
    email: str
    requested_at: datetime
    reported_status: str
    reported_at: datetime
    audit_at: datetime
    request_text: str

    @classmethod
    def from_row(cls, row: Dict[str, str]) -> "DeletionRequest":
        return cls(
            case_id=row["case_id"].strip(),
            email=row["email"].strip().lower(),
            requested_at=datetime.fromisoformat(row["requested_at"].strip().replace("Z", "+00:00")),
            reported_status=row["reported_status"].strip(),
            reported_at=datetime.fromisoformat(row["reported_at"].strip().replace("Z", "+00:00")),
            audit_at=datetime.fromisoformat(row["audit_at"].strip().replace("Z", "+00:00")),
            request_text=row["request_text"].strip(),
        )


@dataclass
class UserIdentity:
    """Represents a current identity record from dataset/user_identities.csv."""
    user_id: str
    name: str
    email: str
    phone: str
    email_hash: str
    updated_at: datetime

    @classmethod
    def from_row(cls, row: Dict[str, str]) -> "UserIdentity":
        return cls(
            user_id=row["user_id"].strip(),
            name=row["name"].strip(),
            email=row["email"].strip().lower(),
            phone=row["phone"].strip(),
            email_hash=row["email_hash"].strip(),
            updated_at=datetime.fromisoformat(row["updated_at"].strip().replace("Z", "+00:00")),
        )


@dataclass
class UserAuditEntry:
    """Represents a historical change row from dataset/user_audit_log.csv."""
    audit_id: str
    user_id: str
    event_time: datetime
    field_name: str
    old_value: str
    new_value: str

    @classmethod
    def from_row(cls, row: Dict[str, str]) -> "UserAuditEntry":
        return cls(
            audit_id=row["audit_id"].strip(),
            user_id=row["user_id"].strip(),
            event_time=datetime.fromisoformat(row["event_time"].strip().replace("Z", "+00:00")),
            field_name=row["field_name"].strip(),
            old_value=row["old_value"].strip(),
            new_value=row["new_value"].strip(),
        )


@dataclass
class UserIdentityGraph:
    """Consolidated graph of all current and historical identifiers for a subject."""
    user_id: str
    names: Set[str] = field(default_factory=set)
    emails: Set[str] = field(default_factory=set)
    phones: Set[str] = field(default_factory=set)
    email_hashes: Set[str] = field(default_factory=set)
    audit_ids: List[str] = field(default_factory=list)

    def matches(self, identifier: Optional[str]) -> bool:
        """Check if an identifier matches any current or historical alias."""
        if not identifier:
            return False
        clean = identifier.strip().lower()
        if clean == self.user_id.lower():
            return True
        if clean in {e.lower() for e in self.emails}:
            return True
        if clean in {p.lower() for p in self.phones}:
            return True
        if clean in {n.lower() for n in self.names}:
            return True
        if clean in {h.lower() for h in self.email_hashes}:
            return True
        return False


@dataclass
class PolicyRule:
    """Represents a policy rule from dataset/deletion_rules.csv."""
    rule_id: str
    data_category: str
    condition: str
    required_action: str

    @classmethod
    def from_row(cls, row: Dict[str, str]) -> "PolicyRule":
        return cls(
            rule_id=row["rule_id"].strip(),
            data_category=row["data_category"].strip(),
            condition=row["condition"].strip(),
            required_action=row["required_action"].strip().upper(),
        )


@dataclass
class SystemActivity:
    """Represents an operational event row from dataset/system_activity.csv."""
    activity_id: str
    event_time: datetime
    event_type: str
    source_system: str
    target_system: str
    resource_id: str
    reported_result: str
    details: str

    @classmethod
    def from_row(cls, row: Dict[str, str]) -> "SystemActivity":
        return cls(
            activity_id=row["activity_id"].strip(),
            event_time=datetime.fromisoformat(row["event_time"].strip().replace("Z", "+00:00")),
            event_type=row["event_type"].strip(),
            source_system=row["source_system"].strip(),
            target_system=row["target_system"].strip(),
            resource_id=row["resource_id"].strip(),
            reported_result=row["reported_result"].strip(),
            details=row["details"].strip(),
        )


@dataclass
class EvidenceManifestEntry:
    """Represents an entry in dataset/evidence_files.csv."""
    file_id: str
    file_path: str
    origin: str
    captured_at: datetime

    @classmethod
    def from_row(cls, row: Dict[str, str]) -> "EvidenceManifestEntry":
        return cls(
            file_id=row["file_id"].strip(),
            file_path=row["file_path"].strip(),
            origin=row["origin"].strip(),
            captured_at=datetime.fromisoformat(row["captured_at"].strip().replace("Z", "+00:00")),
        )


@dataclass
class EvidenceObservation:
    """Preserves an extracted observation from any evidence source."""
    source_file: str
    evidence_id: str
    timestamp: Optional[datetime]
    system_id: str
    resource_id: str
    data_category: Optional[str]
    extracted_state: str  # e.g., PRESENT, ABSENT, REDACTED, ANONYMIZED, ACTIVE, DISABLED, BLOCKED
    identifiers: Dict[str, str] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    extraction_method: str = "unknown"
    is_claim: bool = False  # Activity stream results are claims, not ground truth
    file_captured_at: Optional[datetime] = None


@dataclass
class AuditFinding:
    """Internal representation of a policy violation or recreation risk."""
    system_id: str
    resource_id: str
    operation: Operation
    state: State
    evidence_id: str
    details: str = ""


@dataclass
class AuditStep:
    """Exact grader step schema."""
    step_no: int
    phase: str
    system_id: str
    resource_id: str
    operation: str
    state: str
    evidence_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_no": self.step_no,
            "phase": self.phase,
            "system_id": self.system_id,
            "resource_id": self.resource_id,
            "operation": self.operation,
            "state": self.state,
            "evidence_id": self.evidence_id,
        }


@dataclass
class CasePrediction:
    """Represents the final answer row for a single case in output.csv."""
    case_id: str
    deletion_status: DeletionStatus
    steps: List[AuditStep] = field(default_factory=list)

    def to_row(self) -> Dict[str, str]:
        steps_json = json.dumps([s.to_dict() for s in self.steps], separators=(",", ":"))
        return {
            "case_id": self.case_id,
            "deletion_status": self.deletion_status.value,
            "steps_json": steps_json,
        }


@dataclass
class IngestionWarning:
    """Structured record of a malformed or skipped evidence item."""
    file_id: Optional[str]
    file_path: str
    warning_type: str
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
