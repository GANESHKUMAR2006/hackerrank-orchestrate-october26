"""Synthetic unit tests for DeletionAuditor state reconstruction and drift detection."""

import os
import tempfile
from datetime import datetime, timezone
import pytest

from code.auditor import DeletionAuditor
from code.models import (
    AuditFinding,
    AuditStep,
    DeletionRequest,
    DeletionStatus,
    EvidenceManifestEntry,
    EvidenceObservation,
    Operation,
    Phase,
    State,
    UserIdentityGraph,
)


@pytest.fixture
def auditor() -> DeletionAuditor:
    # Use actual dataset configuration
    return DeletionAuditor("dataset")


def test_auditor_non_deletion_request(auditor: DeletionAuditor) -> None:
    """Non-deletion requests (e.g. data export question) must route to NOT_APPLICABLE."""
    req = DeletionRequest(
        case_id="case_syn_nd",
        email="synthetic.user@example.com",
        requested_at=datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc),
        reported_status="NOT_APPLICABLE",
        reported_at=datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc),
        audit_at=datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc),
        request_text="Can you explain what data you store about my profile?",
    )
    pred = auditor.audit_case(req)
    assert pred.deletion_status == DeletionStatus.NOT_APPLICABLE
    assert pred.steps == []


def test_auditor_future_evidence_exclusion(auditor: DeletionAuditor) -> None:
    """Observations captured strictly after audit_at cannot be used or cited."""
    audit_cutoff = datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc)
    after_cutoff = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)

    # Observation after cutoff
    obs_future = EvidenceObservation(
        source_file="future_snapshot.json",
        evidence_id="evidence_future",
        timestamp=after_cutoff,
        system_id="account_service",
        resource_id="account_syn_future",
        data_category="USER_PROFILE",
        extracted_state="PRESENT",
        identifiers={"email": "future.user@example.com"},
        file_captured_at=after_cutoff,
    )
    auditor.cache._index_observation(obs_future)

    # Querying with cutoff should exclude future observation
    valid_obs = auditor.cache.get_observations_for_resource("account_syn_future", cutoff=audit_cutoff)
    assert len(valid_obs) == 0


def test_auditor_unextracted_image_non_inference(auditor: DeletionAuditor) -> None:
    """Screenshots that are NOT_EXTRACTED must not establish presence or absence."""
    obs_unextracted = EvidenceObservation(
        source_file="console_screenshot.png",
        evidence_id="evidence_img",
        timestamp=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        system_id="account_service",
        resource_id="account_syn_img",
        data_category="USER_PROFILE",
        extracted_state="NOT_EXTRACTED",
        identifiers={"email": "img.user@example.com"},
        file_captured_at=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    auditor.cache._index_observation(obs_unextracted)

    user_graph = UserIdentityGraph(
        user_id="user_syn_img",
        emails={"img.user@example.com"},
    )
    req = DeletionRequest(
        case_id="case_syn_img",
        email="img.user@example.com",
        requested_at=datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc),
        reported_status="COMPLETE",
        reported_at=datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc),
        audit_at=datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc),
        request_text="Please delete all my account data completely.",
    )

    resources = auditor._discover_resources(req, user_graph)
    # The unextracted screenshot observation must NOT be treated as a confirmed resource
    assert "account_syn_img" not in resources


def test_auditor_replication_drift_detection(auditor: DeletionAuditor) -> None:
    """When a primary profile is absent but a secondary replica remains present, drift must be detected."""
    cutoff = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)

    # Primary absent
    obs_primary = EvidenceObservation(
        source_file="primary_database.sql",
        evidence_id="evidence_primary",
        timestamp=datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
        system_id="account_service",
        resource_id="account_syn_drift",
        data_category="USER_PROFILE",
        extracted_state="ABSENT",
        file_captured_at=datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
    )
    # Replica present
    obs_replica = EvidenceObservation(
        source_file="account_replica_snapshot.sql",
        evidence_id="evidence_replica",
        timestamp=datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
        system_id="account_service",
        resource_id="account_syn_drift",
        data_category="USER_PROFILE",
        extracted_state="PRESENT",
        file_captured_at=datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
    )

    auditor.cache._index_observation(obs_primary)
    auditor.cache._index_observation(obs_replica)

    user_graph = UserIdentityGraph(
        user_id="user_syn_drift",
        emails={"drift.user@example.com"},
    )
    req = DeletionRequest(
        case_id="case_syn_drift",
        email="drift.user@example.com",
        requested_at=datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc),
        reported_status="COMPLETE",
        reported_at=datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc),
        audit_at=cutoff,
        request_text="Delete my profile and records.",
    )

    result = auditor._reconstruct_and_evaluate(
        req, user_graph, {"account_syn_drift": "account_service"}
    )
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.operation == Operation.REPORT_REMAINING_RECORD
    assert finding.state == State.PRESENT
    assert finding.evidence_id == "evidence_replica"
