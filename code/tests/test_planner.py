"""Synthetic unit tests for PolicyPlanner."""

import pytest
from datetime import datetime, timezone

from code.models import (
    AuditFinding,
    AuditStep,
    CasePrediction,
    DeletionStatus,
    Operation,
    Phase,
    State,
)
from code.planner import PolicyPlanner


@pytest.fixture
def planner() -> PolicyPlanner:
    return PolicyPlanner()


def test_planner_not_applicable(planner: PolicyPlanner) -> None:
    """Non-deletion requests must produce NOT_APPLICABLE with empty steps."""
    pred = planner.plan_case(
        case_id="case_syn_01",
        is_delete_request=False,
        findings=[],
        verifications=[],
    )
    assert pred.case_id == "case_syn_01"
    assert pred.deletion_status == DeletionStatus.NOT_APPLICABLE
    assert pred.steps == []


def test_planner_complete_case(planner: PolicyPlanner) -> None:
    """Compliant case must produce COMPLETE status with preserved evidence IDs."""
    verifications = [
        AuditStep(
            step_no=0,
            phase=Phase.VERIFICATION.value,
            system_id="account_service",
            resource_id="account_syn_10",
            operation=Operation.VERIFY_RECORD_ABSENT.value,
            state=State.ABSENT.value,
            evidence_id="evidence_syn_01",
        ),
        AuditStep(
            step_no=0,
            phase=Phase.VERIFICATION.value,
            system_id="security_service",
            resource_id="audit_syn_10",
            operation=Operation.VERIFY_RECORD_PRESENT.value,
            state=State.PRESENT.value,
            evidence_id="evidence_syn_01",
        ),
    ]

    pred = planner.plan_case(
        case_id="case_syn_02",
        is_delete_request=True,
        findings=[],
        verifications=verifications,
    )
    assert pred.deletion_status == DeletionStatus.COMPLETE
    assert len(pred.steps) == 2
    assert pred.steps[0].step_no == 1
    assert pred.steps[0].evidence_id == "evidence_syn_01"
    assert pred.steps[1].step_no == 2
    assert pred.steps[1].evidence_id == "evidence_syn_01"


def test_planner_incomplete_phase_ordering(planner: PolicyPlanner) -> None:
    """INCOMPLETE case must enforce FINDING -> REMEDIATION -> VERIFICATION ordering."""
    findings = [
        AuditFinding(
            system_id="account_service",
            resource_id="account_syn_01",
            operation=Operation.REPORT_REMAINING_RECORD,
            state=State.PRESENT,
            evidence_id="evidence_syn_file",
        )
    ]
    verifications = [
        AuditStep(
            step_no=0,
            phase=Phase.VERIFICATION.value,
            system_id="security_service",
            resource_id="audit_syn_01",
            operation=Operation.VERIFY_RECORD_PRESENT.value,
            state=State.PRESENT.value,
            evidence_id="evidence_syn_file",
        )
    ]

    pred = planner.plan_case(
        case_id="case_syn_03",
        is_delete_request=True,
        findings=findings,
        verifications=verifications,
    )

    assert pred.deletion_status == DeletionStatus.INCOMPLETE
    assert len(pred.steps) == 4

    phases = [s.phase for s in pred.steps]
    assert phases == [
        Phase.FINDING.value,
        Phase.REMEDIATION.value,
        Phase.VERIFICATION.value,
        Phase.VERIFICATION.value,
    ]

    # Finding step has actual evidence_id
    assert pred.steps[0].evidence_id == "evidence_syn_file"
    assert pred.steps[0].operation == Operation.REPORT_REMAINING_RECORD.value

    # Remediation step must have evidence_id: ""
    assert pred.steps[1].operation == Operation.DELETE_RECORD.value
    assert pred.steps[1].evidence_id == ""

    # Both post-remediation verifications must have evidence_id: ""
    assert pred.steps[2].evidence_id == ""
    assert pred.steps[3].evidence_id == ""


def test_planner_operation_precedence(planner: PolicyPlanner) -> None:
    """Remediations must order data flows first, then restores, then deletions, redactions, anonymizations."""
    findings = [
        AuditFinding(
            system_id="account_service",
            resource_id="account_syn_01",
            operation=Operation.REPORT_REMAINING_RECORD,
            state=State.PRESENT,
            evidence_id="ev_01",
        ),
        AuditFinding(
            system_id="integration_service",
            resource_id="flow_syn_01",
            operation=Operation.REPORT_ACTIVE_DATA_FLOW,
            state=State.ACTIVE,
            evidence_id="ev_02",
        ),
        AuditFinding(
            system_id="backup_service",
            resource_id="backup_syn_01",
            operation=Operation.REPORT_RESTORE_RISK,
            state=State.ACTIVE,
            evidence_id="ev_03",
        ),
        AuditFinding(
            system_id="analytics_platform",
            resource_id="analytics_syn_01",
            operation=Operation.REPORT_EXPOSED_PII,
            state=State.PRESENT,
            evidence_id="ev_04",
        ),
        AuditFinding(
            system_id="support_platform",
            resource_id="support_syn_01",
            operation=Operation.REPORT_EXPOSED_PII,
            state=State.PRESENT,
            evidence_id="ev_05",
        ),
    ]

    pred = planner.plan_case(
        case_id="case_syn_04",
        is_delete_request=True,
        findings=findings,
        verifications=[],
    )

    remediations = [s for s in pred.steps if s.phase == Phase.REMEDIATION.value]
    rem_ops = [s.operation for s in remediations]

    expected_ops = [
        Operation.DISABLE_DATA_FLOW.value,
        Operation.BLOCK_RESTORE.value,
        Operation.DELETE_RECORD.value,
        Operation.REDACT_RECORD.value,
        Operation.ANONYMIZE_RECORD.value,
    ]
    assert rem_ops == expected_ops


def test_planner_secondary_sorting_and_step_numbers(planner: PolicyPlanner) -> None:
    """Ties within operation must be sorted by system_id then resource_id, with consecutive 1-based numbering."""
    steps = [
        AuditStep(0, Phase.FINDING.value, "search_service", "search_b", Operation.REPORT_REMAINING_RECORD.value, State.PRESENT.value, "e1"),
        AuditStep(0, Phase.FINDING.value, "account_service", "account_b", Operation.REPORT_REMAINING_RECORD.value, State.PRESENT.value, "e2"),
        AuditStep(0, Phase.FINDING.value, "account_service", "account_a", Operation.REPORT_REMAINING_RECORD.value, State.PRESENT.value, "e3"),
        AuditStep(0, Phase.FINDING.value, "search_service", "search_a", Operation.REPORT_REMAINING_RECORD.value, State.PRESENT.value, "e4"),
    ]

    sorted_steps = PolicyPlanner.sort_steps(steps)
    step_nos = [s.step_no for s in sorted_steps]
    assert step_nos == [1, 2, 3, 4]

    resources = [(s.system_id, s.resource_id) for s in sorted_steps]
    assert resources == [
        ("account_service", "account_a"),
        ("account_service", "account_b"),
        ("search_service", "search_a"),
        ("search_service", "search_b"),
    ]
