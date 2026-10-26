"""Synthetic end-to-end pipeline integration tests.

Tests end-to-end execution across intent classification, identity resolution,
evidence filtering, state reconstruction, policy planning, and serialization
using synthetic scenarios not derived from sample output.
"""

from datetime import datetime, timezone
import pytest

from code.auditor import DeletionAuditor
from code.models import (
    DeletionRequest,
    DeletionStatus,
    EvidenceObservation,
    Phase,
)


@pytest.fixture
def auditor() -> DeletionAuditor:
    return DeletionAuditor(dataset_dir="dataset")


def test_e2e_synthetic_not_applicable_inquiry(auditor: DeletionAuditor) -> None:
    """Synthetic E2E Test 1: Non-destructive data retention inquiry routes to NOT_APPLICABLE."""
    req = DeletionRequest(
        case_id="case_syn_e2e_01",
        email="synthetic_inquirer@example.com",
        requested_at=datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc),
        reported_status="NOT_APPLICABLE",
        reported_at=datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc),
        audit_at=datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc),
        request_text="Could you clarify how long our tax and invoice records are kept under your data policy?",
    )

    pred = auditor.audit_case(req)

    assert pred.case_id == "case_syn_e2e_01"
    assert pred.deletion_status == DeletionStatus.NOT_APPLICABLE
    assert pred.steps == []

    # Verify serialization
    row = pred.to_row()
    assert row["case_id"] == "case_syn_e2e_01"
    assert row["deletion_status"] == "NOT_APPLICABLE"
    assert row["steps_json"] == "[]"


def test_e2e_synthetic_complete_clean_tombstone(auditor: DeletionAuditor) -> None:
    """Synthetic E2E Test 2: Compliant case with absent account and redacted tombstone produces COMPLETE."""
    audit_at = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)
    ev_ts = datetime(2026, 9, 14, 12, 0, 0, tzinfo=timezone.utc)
    user_email = "clean.user@example.com"

    # 1. Primary account absent
    auditor.cache._index_observation(
        EvidenceObservation(
            source_file="mock_account_db.sql",
            evidence_id="ev_syn_comp_01",
            timestamp=ev_ts,
            system_id="account_service",
            resource_id="account_syn_clean",
            data_category="USER_PROFILE",
            extracted_state="ABSENT",
            identifiers={"email": user_email},
            file_captured_at=ev_ts,
        )
    )

    # 2. Security audit record retained under compliance
    auditor.cache._index_observation(
        EvidenceObservation(
            source_file="mock_audit_log.json",
            evidence_id="ev_syn_comp_02",
            timestamp=ev_ts,
            system_id="security_service",
            resource_id="audit_syn_clean",
            data_category="SECURITY_AUDIT_LOG",
            extracted_state="PRESENT",
            identifiers={"email": user_email},
            file_captured_at=ev_ts,
        )
    )

    # 3. Tombstone in identity_service with PII redacted
    auditor.cache._index_observation(
        EvidenceObservation(
            source_file="mock_tombstone_bundle.json",
            evidence_id="ev_syn_comp_03",
            timestamp=ev_ts,
            system_id="identity_service",
            resource_id="tombstone_syn_clean",
            data_category="ACCOUNT_TOMBSTONE",
            extracted_state="REDACTED",
            identifiers={"email": user_email},
            file_captured_at=ev_ts,
        )
    )

    req = DeletionRequest(
        case_id="case_syn_e2e_02",
        email=user_email,
        requested_at=datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
        reported_status="COMPLETE",
        reported_at=datetime(2026, 9, 12, 10, 0, 0, tzinfo=timezone.utc),
        audit_at=audit_at,
        request_text="Please delete my account and personal data permanently. Keeping an internal tombstone reference is acceptable.",
    )

    pred = auditor.audit_case(req)

    assert pred.case_id == "case_syn_e2e_02"
    assert pred.deletion_status == DeletionStatus.COMPLETE
    assert len(pred.steps) == 3

    # Every step must be VERIFICATION and preserve verified evidence_id
    for step in pred.steps:
        assert step.phase == Phase.VERIFICATION.value
        assert step.evidence_id != ""

    # Verify consecutive 1-based numbering
    assert [s.step_no for s in pred.steps] == [1, 2, 3]


def test_e2e_synthetic_incomplete_multi_service_violations(auditor: DeletionAuditor) -> None:
    """Synthetic E2E Test 3: INCOMPLETE case with replication drift and active connector."""
    audit_at = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)
    ev_ts = datetime(2026, 9, 14, 10, 0, 0, tzinfo=timezone.utc)
    drift_email = "drift.user@example.com"

    # Primary absent, but replica snapshot shows record still PRESENT
    auditor.cache._index_observation(
        EvidenceObservation(
            source_file="account_primary_snapshot.sql",
            evidence_id="ev_syn_drift_pri",
            timestamp=ev_ts,
            system_id="account_service",
            resource_id="account_syn_drift",
            data_category="USER_PROFILE",
            extracted_state="ABSENT",
            identifiers={"email": drift_email},
            file_captured_at=ev_ts,
        )
    )
    auditor.cache._index_observation(
        EvidenceObservation(
            source_file="account_replica_secondary.sql",
            evidence_id="ev_syn_drift_rep",
            timestamp=ev_ts,
            system_id="account_service",
            resource_id="account_syn_drift",
            data_category="USER_PROFILE",
            extracted_state="PRESENT",
            identifiers={"email": drift_email},
            file_captured_at=ev_ts,
        )
    )

    # Active integration data flow
    auditor.cache._index_observation(
        EvidenceObservation(
            source_file="service_event_log.log",
            evidence_id="ev_syn_flow",
            timestamp=ev_ts,
            system_id="integration_service",
            resource_id="flow_syn_active",
            data_category="connector_heartbeat",
            extracted_state="ACTIVE",
            identifiers={"email": drift_email},
            file_captured_at=ev_ts,
        )
    )

    req = DeletionRequest(
        case_id="case_syn_e2e_03",
        email=drift_email,
        requested_at=datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
        reported_status="COMPLETE",
        reported_at=datetime(2026, 9, 12, 10, 0, 0, tzinfo=timezone.utc),
        audit_at=audit_at,
        request_text="Please permanently delete my account and remove all personal data.",
    )

    pred = auditor.audit_case(req)

    assert pred.case_id == "case_syn_e2e_03"
    assert pred.deletion_status == DeletionStatus.INCOMPLETE

    phases = [s.phase for s in pred.steps]
    # Check strict phase sequencing: FINDING -> REMEDIATION -> VERIFICATION
    assert Phase.FINDING.value in phases
    assert Phase.REMEDIATION.value in phases
    assert Phase.VERIFICATION.value in phases

    first_rem_idx = phases.index(Phase.REMEDIATION.value)
    first_ver_idx = phases.index(Phase.VERIFICATION.value)
    assert first_rem_idx > 0
    assert first_ver_idx > first_rem_idx

    # Check that remediations and post-remediation verifications have empty citations
    for step in pred.steps:
        if step.phase in {Phase.REMEDIATION.value, Phase.VERIFICATION.value}:
            assert step.evidence_id == ""
        elif step.phase == Phase.FINDING.value:
            assert step.evidence_id != ""

    # Check 1-based step numbering
    assert [s.step_no for s in pred.steps] == list(range(1, len(pred.steps) + 1))
