"""Unit tests for code/models.py."""

from datetime import datetime, timezone
import json
import pytest

from code.models import (
    AuditStep,
    CasePrediction,
    DeletionRequest,
    DeletionStatus,
    EvidenceManifestEntry,
    EvidenceObservation,
    Operation,
    Phase,
    PolicyRule,
    State,
    SystemActivity,
    UserAuditEntry,
    UserIdentity,
    UserIdentityGraph,
)


def test_deletion_request_from_row():
    row = {
        "case_id": "case_test_01",
        "email": "USER.TEST@EXAMPLE.COM ",
        "requested_at": "2026-08-18T09:14:00Z",
        "reported_status": "COMPLETE",
        "reported_at": "2026-08-20T16:42:00Z",
        "audit_at": "2026-09-03T11:30:00Z",
        "request_text": "Please delete my account data.",
    }
    req = DeletionRequest.from_row(row)
    assert req.case_id == "case_test_01"
    assert req.email == "user.test@example.com"
    assert req.reported_status == "COMPLETE"
    assert req.audit_at == datetime(2026, 9, 3, 11, 30, tzinfo=timezone.utc)


def test_user_identity_and_graph_matching():
    ident = UserIdentity(
        user_id="user_999",
        name="Alex Smith",
        email="alex.smith@example.com",
        phone="+1 555 0199",
        email_hash="hash_999",
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    graph = UserIdentityGraph(
        user_id=ident.user_id,
        names={ident.name, "Alexander Smith"},
        emails={ident.email, "asmith_old@example.com"},
        phones={ident.phone},
        email_hashes={ident.email_hash},
    )

    # Current email
    assert graph.matches("alex.smith@example.com")
    assert graph.matches("ALEX.SMITH@EXAMPLE.COM")
    # Historical email
    assert graph.matches("asmith_old@example.com")
    # User ID
    assert graph.matches("user_999")
    # Phone
    assert graph.matches("+1 555 0199")
    # Name
    assert graph.matches("Alexander Smith")
    # Hash
    assert graph.matches("hash_999")
    # Unrelated
    assert not graph.matches("unrelated@example.com")
    assert not graph.matches(None)
    assert not graph.matches("")


def test_audit_step_serialization():
    step = AuditStep(
        step_no=1,
        phase="FINDING",
        system_id="account_service",
        resource_id="account_005",
        operation="REPORT_REMAINING_RECORD",
        state="PRESENT",
        evidence_id="evidence_54",
    )
    d = step.to_dict()
    assert d["step_no"] == 1
    assert d["phase"] == "FINDING"
    assert d["system_id"] == "account_service"
    assert d["resource_id"] == "account_005"
    assert d["operation"] == "REPORT_REMAINING_RECORD"
    assert d["state"] == "PRESENT"
    assert d["evidence_id"] == "evidence_54"


def test_case_prediction_to_row():
    pred = CasePrediction(
        case_id="case_000",
        deletion_status=DeletionStatus.NOT_APPLICABLE,
        steps=[],
    )
    row = pred.to_row()
    assert row["case_id"] == "case_000"
    assert row["deletion_status"] == "NOT_APPLICABLE"
    assert row["steps_json"] == "[]"

    # Incomplete case with steps
    step = AuditStep(
        step_no=1,
        phase="FINDING",
        system_id="account_service",
        resource_id="account_001",
        operation="REPORT_REMAINING_RECORD",
        state="PRESENT",
        evidence_id="evidence_01",
    )
    pred_inc = CasePrediction(
        case_id="case_001",
        deletion_status=DeletionStatus.INCOMPLETE,
        steps=[step],
    )
    row_inc = pred_inc.to_row()
    assert row_inc["deletion_status"] == "INCOMPLETE"
    parsed_json = json.loads(row_inc["steps_json"])
    assert len(parsed_json) == 1
    assert parsed_json[0]["step_no"] == 1
    assert parsed_json[0]["evidence_id"] == "evidence_01"


def test_policy_rule_and_system_activity():
    rule = PolicyRule.from_row({
        "rule_id": "rule_01",
        "data_category": "USER_PROFILE",
        "condition": "Always",
        "required_action": "DELETE",
    })
    assert rule.required_action == "DELETE"

    activity = SystemActivity.from_row({
        "activity_id": "act_01",
        "event_time": "2026-01-04T14:56:29Z",
        "event_type": "INDEX_RECORD",
        "source_system": "account_service",
        "target_system": "search_service",
        "resource_id": "search_9729",
        "reported_result": "SUCCESS",
        "details": "Customer search-index refresh.",
    })
    assert activity.activity_id == "act_01"
    assert activity.reported_result == "SUCCESS"
