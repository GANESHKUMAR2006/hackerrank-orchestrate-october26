"""Synthetic regression test suite for HackerRank Orchestrate: Ghost Data Still Exists.

Covers:
1. Primary record deleted while secondary replica retains it (replication drift).
2. Compliant retained record (policy-permitted retention e.g. Rule 12 security audit logs).
3. Tombstone with direct PII (Rule 15 violation requiring redaction).
4. Active restore risk via deletion_block=false / restore_allowed=true (Rule 14 violation).
5. Evidence captured after audit cutoff strictly excluded from historical determination.
6. Operation precedence, ordering ties, and non-deletion request handling.
"""

from datetime import datetime, timezone
import pytest

from code.auditor import DeletionAuditor
from code.models import (
    AuditFinding,
    AuditStep,
    DeletionRequest,
    DeletionStatus,
    EvidenceObservation,
    Operation,
    Phase,
    State,
    UserIdentityGraph,
)
from code.planner import PolicyPlanner


@pytest.fixture
def auditor() -> DeletionAuditor:
    return DeletionAuditor("dataset")


@pytest.fixture
def planner() -> PolicyPlanner:
    return PolicyPlanner()


def test_regression_primary_deleted_while_replica_retains(auditor: DeletionAuditor) -> None:
    """Primary record deleted while secondary replica retains it triggers drift finding and remediation."""
    cutoff = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)

    # Primary absent observation
    obs_primary = EvidenceObservation(
        source_file="primary_cluster.sql",
        evidence_id="ev_pri",
        timestamp=datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
        system_id="account_service",
        resource_id="account_reg_drift",
        data_category="USER_PROFILE",
        extracted_state="ABSENT",
        file_captured_at=datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
    )
    # Replica still present observation
    obs_replica = EvidenceObservation(
        source_file="failover_replica.sql",
        evidence_id="ev_rep",
        timestamp=datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
        system_id="account_service",
        resource_id="account_reg_drift",
        data_category="USER_PROFILE",
        extracted_state="PRESENT",
        file_captured_at=datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
    )

    auditor.cache._index_observation(obs_primary)
    auditor.cache._index_observation(obs_replica)

    user_graph = UserIdentityGraph(
        user_id="user_reg_drift",
        emails={"drift.regression@example.com"},
    )
    req = DeletionRequest(
        case_id="case_reg_drift",
        email="drift.regression@example.com",
        requested_at=datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc),
        reported_status="COMPLETE",
        reported_at=datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc),
        audit_at=cutoff,
        request_text="Please delete my account data completely.",
    )

    eval_res = auditor._reconstruct_and_evaluate(
        req, user_graph, {"account_reg_drift": "account_service"}
    )
    assert len(eval_res.findings) == 1
    finding = eval_res.findings[0]
    assert finding.operation == Operation.REPORT_REMAINING_RECORD
    assert finding.state == State.PRESENT
    assert finding.evidence_id == "ev_rep"

    prediction = auditor.planner.plan_case(
        case_id=req.case_id,
        is_delete_request=True,
        findings=eval_res.findings,
        verifications=eval_res.verifications,
    )
    assert prediction.deletion_status == DeletionStatus.INCOMPLETE
    phases = [s.phase for s in prediction.steps]
    assert phases == [
        Phase.FINDING.value,
        Phase.REMEDIATION.value,
        Phase.VERIFICATION.value,
    ]
    assert prediction.steps[0].evidence_id == "ev_rep"
    assert prediction.steps[1].evidence_id == ""
    assert prediction.steps[2].evidence_id == ""


def test_regression_compliant_retained_record(auditor: DeletionAuditor) -> None:
    """Policy-compliant retained security audit log must produce VERIFY_RECORD_PRESENT with evidence citation."""
    cutoff = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)

    # Compliant security audit log retained within legal period (Rule 12)
    obs_security = EvidenceObservation(
        source_file="security_audit_export.json",
        evidence_id="ev_sec",
        timestamp=datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
        system_id="security_service",
        resource_id="audit_record_reg_01",
        data_category="SECURITY_AUDIT_LOG",
        extracted_state="PRESENT",
        identifiers={"user_id": "user_reg_compliant"},
        file_captured_at=datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
    )
    # Absent account
    obs_account = EvidenceObservation(
        source_file="account_export.json",
        evidence_id="ev_acc",
        timestamp=datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
        system_id="account_service",
        resource_id="account_reg_compliant",
        data_category="USER_PROFILE",
        extracted_state="ABSENT",
        identifiers={"user_id": "user_reg_compliant"},
        file_captured_at=datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
    )

    auditor.cache._index_observation(obs_security)
    auditor.cache._index_observation(obs_account)

    user_graph = UserIdentityGraph(
        user_id="user_reg_compliant",
        emails={"compliant@example.com"},
    )
    req = DeletionRequest(
        case_id="case_reg_compliant",
        email="compliant@example.com",
        requested_at=datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc),
        reported_status="COMPLETE",
        reported_at=datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc),
        audit_at=cutoff,
        request_text="Please delete my account data. Security logs can be kept.",
    )

    eval_res = auditor._reconstruct_and_evaluate(
        req,
        user_graph,
        {
            "account_reg_compliant": "account_service",
            "audit_record_reg_01": "security_service",
        },
    )
    assert len(eval_res.findings) == 0

    prediction = auditor.planner.plan_case(
        case_id=req.case_id,
        is_delete_request=True,
        findings=eval_res.findings,
        verifications=eval_res.verifications,
    )
    assert prediction.deletion_status == DeletionStatus.COMPLETE
    # Verified steps must cite valid historical evidence
    sec_step = next(s for s in prediction.steps if s.system_id == "security_service")
    assert sec_step.operation == Operation.VERIFY_RECORD_PRESENT.value
    assert sec_step.state == State.PRESENT.value
    assert sec_step.evidence_id == "ev_sec"


def test_regression_tombstone_with_direct_pii(auditor: DeletionAuditor) -> None:
    """Tombstone retaining direct PII violates Rule 15 and triggers REPORT_EXPOSED_PII finding."""
    cutoff = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)

    # Tombstone observation with unredacted personal email
    obs_tombstone = EvidenceObservation(
        source_file="identity_store.json",
        evidence_id="ev_tomb",
        timestamp=datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
        system_id="identity_service",
        resource_id="tombstone_reg_01",
        data_category="ACCOUNT_TOMBSTONE",
        extracted_state="PRESENT",
        identifiers={"email": "pii.tombstone@example.com", "user_id": "user_reg_tomb"},
        file_captured_at=datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
    )
    auditor.cache._index_observation(obs_tombstone)

    user_graph = UserIdentityGraph(
        user_id="user_reg_tomb",
        emails={"pii.tombstone@example.com"},
    )
    req = DeletionRequest(
        case_id="case_reg_tomb",
        email="pii.tombstone@example.com",
        requested_at=datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc),
        reported_status="COMPLETE",
        reported_at=datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc),
        audit_at=cutoff,
        request_text="Delete my account and ensure no identifiers remain.",
    )

    eval_res = auditor._reconstruct_and_evaluate(
        req, user_graph, {"tombstone_reg_01": "identity_service"}
    )
    assert len(eval_res.findings) == 1
    finding = eval_res.findings[0]
    assert finding.operation == Operation.REPORT_EXPOSED_PII
    assert finding.state == State.PRESENT
    assert finding.evidence_id == "ev_tomb"

    prediction = auditor.planner.plan_case(
        case_id=req.case_id,
        is_delete_request=True,
        findings=eval_res.findings,
        verifications=eval_res.verifications,
    )
    assert prediction.deletion_status == DeletionStatus.INCOMPLETE
    rem_step = next(s for s in prediction.steps if s.phase == Phase.REMEDIATION.value)
    assert rem_step.operation == Operation.REDACT_RECORD.value
    assert rem_step.state == State.REDACTED.value
    assert rem_step.evidence_id == ""


def test_regression_active_restore_risk_deletion_block_false(auditor: DeletionAuditor) -> None:
    """Active backup restore risk (restore_allowed=true) triggers Rule 14 restore risk finding."""
    cutoff = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)

    # Backup entry with restore enabled
    obs_backup = EvidenceObservation(
        source_file="backup_catalog.json",
        evidence_id="ev_backup",
        timestamp=datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
        system_id="backup_service",
        resource_id="backup_reg_01",
        data_category="BACKUP_ARCHIVE",
        extracted_state="ACTIVE",
        identifiers={"user_id": "user_reg_backup"},
        file_captured_at=datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
    )
    auditor.cache._index_observation(obs_backup)

    user_graph = UserIdentityGraph(
        user_id="user_reg_backup",
        emails={"backup.risk@example.com"},
    )
    req = DeletionRequest(
        case_id="case_reg_backup",
        email="backup.risk@example.com",
        requested_at=datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc),
        reported_status="COMPLETE",
        reported_at=datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc),
        audit_at=cutoff,
        request_text="Please delete all data and block any restore possibilities.",
    )

    eval_res = auditor._reconstruct_and_evaluate(
        req, user_graph, {"backup_reg_01": "backup_service"}
    )
    assert len(eval_res.findings) == 1
    finding = eval_res.findings[0]
    assert finding.operation == Operation.REPORT_RESTORE_RISK
    assert finding.state == State.ACTIVE
    assert finding.evidence_id == "ev_backup"

    prediction = auditor.planner.plan_case(
        case_id=req.case_id,
        is_delete_request=True,
        findings=eval_res.findings,
        verifications=eval_res.verifications,
    )
    assert prediction.deletion_status == DeletionStatus.INCOMPLETE
    rem_step = next(s for s in prediction.steps if s.phase == Phase.REMEDIATION.value)
    assert rem_step.operation == Operation.BLOCK_RESTORE.value
    assert rem_step.state == State.BLOCKED.value
    assert rem_step.evidence_id == ""

    post_ver = next(
        s for s in prediction.steps
        if s.phase == Phase.VERIFICATION.value and s.system_id == "backup_service"
    )
    assert post_ver.operation == Operation.VERIFY_RESTORE_BLOCKED.value
    assert post_ver.state == State.BLOCKED.value
    assert post_ver.evidence_id == ""


def test_regression_evidence_after_cutoff_excluded(auditor: DeletionAuditor) -> None:
    """Observations captured strictly after audit_at must never be used to evaluate historical state."""
    cutoff = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)
    after_cutoff = datetime(2026, 9, 16, 12, 0, 0, tzinfo=timezone.utc)

    # Observation recorded after cutoff
    obs_post = EvidenceObservation(
        source_file="future_run.json",
        evidence_id="ev_post_cutoff",
        timestamp=after_cutoff,
        system_id="search_service",
        resource_id="search_reg_post",
        data_category="SEARCH_INDEX_ENTRY",
        extracted_state="PRESENT",
        identifiers={"user_id": "user_post_cutoff"},
        file_captured_at=after_cutoff,
    )
    auditor.cache._index_observation(obs_post)

    # get_observations_for_resource with cutoff must filter out the future observation
    valid_obs = auditor.cache.get_observations_for_resource("search_reg_post", cutoff=cutoff)
    assert len(valid_obs) == 0


def test_regression_ordering_ties_and_non_deletion_requests(planner: PolicyPlanner) -> None:
    """Steps must be strictly sorted by Phase -> Operation rank -> System ID -> Resource ID, and non-deletions return empty array."""
    # 1. Non-deletion case
    non_del_pred = planner.plan_case(
        case_id="case_non_del_01",
        is_delete_request=False,
        findings=[
            AuditFinding(
                system_id="account_service",
                resource_id="account_001",
                operation=Operation.REPORT_REMAINING_RECORD,
                state=State.PRESENT,
                evidence_id="ev_1",
            )
        ],
        verifications=[],
    )
    assert non_del_pred.deletion_status == DeletionStatus.NOT_APPLICABLE
    assert non_del_pred.steps == []

    # 2. Strict ordering ties across multiple systems and operations
    raw_steps = [
        AuditStep(
            step_no=0,
            phase=Phase.VERIFICATION.value,
            system_id="security_service",
            resource_id="audit_record_02",
            operation=Operation.VERIFY_RECORD_PRESENT.value,
            state=State.PRESENT.value,
            evidence_id="",
        ),
        AuditStep(
            step_no=0,
            phase=Phase.FINDING.value,
            system_id="search_service",
            resource_id="search_01",
            operation=Operation.REPORT_REMAINING_RECORD.value,
            state=State.PRESENT.value,
            evidence_id="ev_s",
        ),
        AuditStep(
            step_no=0,
            phase=Phase.REMEDIATION.value,
            system_id="search_service",
            resource_id="search_01",
            operation=Operation.DELETE_RECORD.value,
            state=State.ABSENT.value,
            evidence_id="",
        ),
        AuditStep(
            step_no=0,
            phase=Phase.REMEDIATION.value,
            system_id="integration_service",
            resource_id="flow_01",
            operation=Operation.DISABLE_DATA_FLOW.value,
            state=State.DISABLED.value,
            evidence_id="",
        ),
        AuditStep(
            step_no=0,
            phase=Phase.FINDING.value,
            system_id="account_service",
            resource_id="account_01",
            operation=Operation.REPORT_REMAINING_RECORD.value,
            state=State.PRESENT.value,
            evidence_id="ev_a",
        ),
    ]

    sorted_steps = planner.sort_steps(raw_steps)
    # Check step numbering: 1-based, consecutive
    assert [s.step_no for s in sorted_steps] == [1, 2, 3, 4, 5]

    # Check phase ordering: FINDING (0,1), REMEDIATION (2,3), VERIFICATION (4)
    assert sorted_steps[0].phase == Phase.FINDING.value
    assert sorted_steps[1].phase == Phase.FINDING.value
    assert sorted_steps[2].phase == Phase.REMEDIATION.value
    assert sorted_steps[3].phase == Phase.REMEDIATION.value
    assert sorted_steps[4].phase == Phase.VERIFICATION.value

    # Check system_id tie break in FINDING: account_service < search_service
    assert sorted_steps[0].system_id == "account_service"
    assert sorted_steps[1].system_id == "search_service"

    # Check remediation operation precedence: DISABLE_DATA_FLOW (rank 0) < DELETE_RECORD (rank 2)
    assert sorted_steps[2].operation == Operation.DISABLE_DATA_FLOW.value
    assert sorted_steps[3].operation == Operation.DELETE_RECORD.value
