"""Remediation policy planner and deterministic step synthesizer.

Synthesizes ordered AuditStep sequences from state findings and verified compliant
resources, enforcing the 5-level operation hierarchy and empty citation contracts.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from code.models import (
    AuditFinding,
    AuditStep,
    CasePrediction,
    DeletionStatus,
    Operation,
    Phase,
    State,
)

# Sorting hierarchy: Phase order -> Operation precedence -> System ID -> Resource ID
PHASE_ORDER: Dict[str, int] = {
    Phase.FINDING.value: 0,
    Phase.REMEDIATION.value: 1,
    Phase.VERIFICATION.value: 2,
}

OP_ORDER: Dict[str, Dict[str, int]] = {
    Phase.FINDING.value: {
        Operation.REPORT_REMAINING_RECORD.value: 0,
        Operation.REPORT_EXPOSED_PII.value: 1,
        Operation.REPORT_ACTIVE_DATA_FLOW.value: 2,
        Operation.REPORT_RESTORE_RISK.value: 3,
    },
    Phase.REMEDIATION.value: {
        Operation.DISABLE_DATA_FLOW.value: 0,
        Operation.BLOCK_RESTORE.value: 1,
        Operation.DELETE_RECORD.value: 2,
        Operation.REDACT_RECORD.value: 3,
        Operation.ANONYMIZE_RECORD.value: 4,
    },
    Phase.VERIFICATION.value: {
        Operation.VERIFY_RECORD_ABSENT.value: 0,
        Operation.VERIFY_RECORD_PRESENT.value: 1,
        Operation.VERIFY_RECORD_REDACTED.value: 2,
        Operation.VERIFY_RECORD_ANONYMIZED.value: 3,
        Operation.VERIFY_DATA_FLOW_DISABLED.value: 4,
        Operation.VERIFY_RESTORE_BLOCKED.value: 5,
    },
}


class PolicyPlanner:
    """Plans remediation sequences and verifies state across audited resources."""

    @staticmethod
    def sort_steps(steps: List[AuditStep]) -> List[AuditStep]:
        """Enforce strict 5-level sorting hierarchy and consecutive 1-based step numbering."""

        def sort_key(s: AuditStep) -> Tuple[int, int, str, str]:
            p_idx = PHASE_ORDER.get(s.phase, 99)
            op_idx = OP_ORDER.get(s.phase, {}).get(s.operation, 99)
            return (p_idx, op_idx, s.system_id, s.resource_id)

        sorted_list = sorted(steps, key=sort_key)
        for i, step in enumerate(sorted_list, start=1):
            step.step_no = i
        return sorted_list

    def plan_case(
        self,
        case_id: str,
        is_delete_request: bool,
        findings: List[AuditFinding],
        verifications: List[AuditStep],
    ) -> CasePrediction:
        """Synthesize a complete CasePrediction from classified intent, findings, and verifications."""
        if not is_delete_request:
            return CasePrediction(
                case_id=case_id,
                deletion_status=DeletionStatus.NOT_APPLICABLE,
                steps=[],
            )

        final_steps: List[AuditStep] = []

        if findings:
            deletion_status = DeletionStatus.INCOMPLETE

            # Phase 1: Findings (cite observed evidence)
            for f in findings:
                final_steps.append(
                    AuditStep(
                        step_no=0,
                        phase=Phase.FINDING.value,
                        system_id=f.system_id,
                        resource_id=f.resource_id,
                        operation=f.operation.value,
                        state=f.state.value,
                        evidence_id=f.evidence_id,
                    )
                )

            # Phase 2: Remediation (must have evidence_id: "")
            for f in findings:
                rem_op, rem_state = self._map_remediation(f)
                final_steps.append(
                    AuditStep(
                        step_no=0,
                        phase=Phase.REMEDIATION.value,
                        system_id=f.system_id,
                        resource_id=f.resource_id,
                        operation=rem_op.value,
                        state=rem_state.value,
                        evidence_id="",
                    )
                )

            # Phase 3: Post-remediation Verifications
            # For INCOMPLETE cases, all verification steps are post-remediation checks, so evidence_id=""
            for v in verifications:
                final_steps.append(
                    AuditStep(
                        step_no=0,
                        phase=Phase.VERIFICATION.value,
                        system_id=v.system_id,
                        resource_id=v.resource_id,
                        operation=v.operation,
                        state=v.state,
                        evidence_id="",
                    )
                )

            for f in findings:
                v_op, v_state = self._map_post_remediation_verification(f)
                final_steps.append(
                    AuditStep(
                        step_no=0,
                        phase=Phase.VERIFICATION.value,
                        system_id=f.system_id,
                        resource_id=f.resource_id,
                        operation=v_op.value,
                        state=v_state.value,
                        evidence_id="",
                    )
                )

        else:
            deletion_status = DeletionStatus.COMPLETE
            # For COMPLETE cases, verifications preserve their verified historical evidence citation
            for v in verifications:
                final_steps.append(
                    AuditStep(
                        step_no=0,
                        phase=Phase.VERIFICATION.value,
                        system_id=v.system_id,
                        resource_id=v.resource_id,
                        operation=v.operation,
                        state=v.state,
                        evidence_id=v.evidence_id,
                    )
                )

        sorted_steps = self.sort_steps(final_steps)
        return CasePrediction(
            case_id=case_id,
            deletion_status=deletion_status,
            steps=sorted_steps,
        )

    @staticmethod
    def _map_remediation(finding: AuditFinding) -> Tuple[Operation, State]:
        """Determine required remediation operation and target state for a violation finding."""
        if finding.operation == Operation.REPORT_ACTIVE_DATA_FLOW:
            return Operation.DISABLE_DATA_FLOW, State.DISABLED
        if finding.operation == Operation.REPORT_RESTORE_RISK:
            return Operation.BLOCK_RESTORE, State.BLOCKED
        if finding.operation == Operation.REPORT_REMAINING_RECORD:
            return Operation.DELETE_RECORD, State.ABSENT
        if finding.operation == Operation.REPORT_EXPOSED_PII:
            if finding.system_id == "analytics_platform":
                return Operation.ANONYMIZE_RECORD, State.ANONYMIZED
            return Operation.REDACT_RECORD, State.REDACTED

        # Default fallback to record deletion
        return Operation.DELETE_RECORD, State.ABSENT

    @staticmethod
    def _map_post_remediation_verification(finding: AuditFinding) -> Tuple[Operation, State]:
        """Determine corresponding post-remediation verification check for a violation finding."""
        if finding.operation == Operation.REPORT_ACTIVE_DATA_FLOW:
            return Operation.VERIFY_DATA_FLOW_DISABLED, State.DISABLED
        if finding.operation == Operation.REPORT_RESTORE_RISK:
            return Operation.VERIFY_RESTORE_BLOCKED, State.BLOCKED
        if finding.operation == Operation.REPORT_REMAINING_RECORD:
            return Operation.VERIFY_RECORD_ABSENT, State.ABSENT
        if finding.operation == Operation.REPORT_EXPOSED_PII:
            if finding.system_id == "analytics_platform":
                return Operation.VERIFY_RECORD_ANONYMIZED, State.ANONYMIZED
            return Operation.VERIFY_RECORD_REDACTED, State.REDACTED

        return Operation.VERIFY_RECORD_ABSENT, State.ABSENT
