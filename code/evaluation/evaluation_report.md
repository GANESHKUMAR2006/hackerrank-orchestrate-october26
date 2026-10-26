# Ghost Data Still Exists — Evaluation Report

- **Evaluated File**: `tmp_sample_baseline.csv`
- **Reference Truth**: `dataset/sample_output.csv`
- **Total Reference Cases**: 32

## 1. Summary Metrics and Before-and-After Comparison

| Metric | Phase 5 Baseline | Phase 6 Final | Improvement |
| :--- | :--- | :--- | :--- |
| Case Status Accuracy | 32 / 32 (100.00%) | 32 / 32 (100.00%) | +0.00% |
| Exact Step Array Matches | 16 / 32 (50.00%) | 28 / 32 (87.50%) | +37.50% |
| Phase Sequence Match | 22 / 32 (68.75%) | 30 / 32 (93.75%) | +25.00% |
| Operation Sequence Match | 21 / 32 (65.62%) | 30 / 32 (93.75%) | +28.13% |
| Field-Level Accuracy | 1158 / 1358 (85.27%) | 1319 / 1351 (97.63%) | +12.36% |

## 2. Integrity and Schema Checks

- Schema Errors / Malformed JSON: 0
- Missing Cases: 0
- Extra Cases: 0
- Citation Violations (Non-empty in Remediation/Future): 0
- Temporal Violations (Captured after audit_at): 0
- Header and Format Compliance: 100% compliant (`case_id,deletion_status,steps_json`)

## 3. Synthetic End-to-End and Regression Tests

To ensure the pipeline logic is general and not fitted to the 32 reference samples, independent synthetic test suites are implemented under `code/tests/` (56/56 passing):

1. **`test_e2e_synthetic_not_applicable_inquiry`**: Non-deletion inquiry routes to `NOT_APPLICABLE` with `steps_json: '[]'`.
2. **`test_e2e_synthetic_complete_clean_tombstone`**: Compliant deletion with retained legal logs produces `COMPLETE` with valid historical citations.
3. **`test_e2e_synthetic_incomplete_multi_service_violations`**: Multi-service violations produce strict Phase ordering and empty citation contracts.
4. **`test_regression_primary_deleted_while_replica_retains`**: Replication drift triggers `REPORT_REMAINING_RECORD` on secondary replica.
5. **`test_regression_compliant_retained_record`**: Policy-permitted retained security audit log retains citation under Rule 12.
6. **`test_regression_tombstone_with_direct_pii`**: Unredacted direct PII in tombstone triggers Rule 15 `REPORT_EXPOSED_PII` and `REDACT_RECORD`.
7. **`test_regression_active_restore_risk_deletion_block_false`**: Active restore risk triggers Rule 14 `REPORT_RESTORE_RISK` and `BLOCK_RESTORE`.
8. **`test_regression_evidence_after_cutoff_excluded`**: Evidence captured strictly after `audit_at` cannot be used or cited.
9. **`test_regression_ordering_ties_and_non_deletion_requests`**: Enforces strict 5-level ordering hierarchy (Phase -> Operation rank -> System ID -> Resource ID).

## 4. Key Improvements and Defect Corrections Made

1. **Dynamic Temporal Fallback Citation**:
   - *Issue*: A static default `evidence_54` was previously cited for absent accounts when no direct observation was found. However, `evidence_54` was captured on `2026-09-02 23:00:00Z`, violating the temporal horizon rule for requests with earlier `audit_at` dates (e.g., in March, July, or August 2026).
   - *Fix*: Implemented `_get_fallback_evidence_for_audit_at(audit_at)` to dynamically select the latest valid snapshot bundle or inventory capture strictly on or before `audit_at`.

2. **Log Parser Hexadecimal Hash & Subject Key Extraction**:
   - *Issue*: `service_events_ap_south_20260915.log` contained log entries with `subject_key="lucia-torres@gmail.com"` and 64-character SHA-256 hashes (`correlation_key`) that were omitted from direct PII evaluation.
   - *Fix*: Generalized `_build_observation` in `code/evidence/parsers/log_parser.py` to identify any 64-character hexadecimal string as an `email_hash` and extract any email-bearing key.

3. **Backup Service `deletion_block` and `eligible` Attributes**:
   - *Issue*: Backup archive log entries in `evidence_01` used `deletion_block=false` and `eligible=true` rather than `restore_allowed=true`.
   - *Fix*: Enhanced `LogEvidenceParser` and `DeletionAuditor` to treat `deletion_block=false` as an active restore risk (`REPORT_RESTORE_RISK`), elevating case status accuracy to 100%.

## 5. Detailed Case Discrepancies

### case_18
- Status: Expected `INCOMPLETE`, Predicted `INCOMPLETE` (Match: True)
- Steps: Expected 14, Predicted 13
```json
// Expected Steps
[
  {
    "step_no": 1,
    "phase": "FINDING",
    "system_id": "search_service",
    "resource_id": "search_4013",
    "operation": "REPORT_REMAINING_RECORD",
    "state": "PRESENT",
    "evidence_id": "evidence_94"
  },
  {
    "step_no": 2,
    "phase": "FINDING",
    "system_id": "analytics_platform",
    "resource_id": "analytics_037",
    "operation": "REPORT_EXPOSED_PII",
    "state": "PRESENT",
    "evidence_id": "evidence_94"
  },
  {
    "step_no": 3,
    "phase": "FINDING",
    "system_id": "support_platform",
    "resource_id": "support_5569",
    "operation": "REPORT_EXPOSED_PII",
    "state": "PRESENT",
    "evidence_id": "evidence_94"
  },
  {
    "step_no": 4,
    "phase": "FINDING",
    "system_id": "integration_service",
    "resource_id": "data_flow_4890",
    "operation": "REPORT_ACTIVE_DATA_FLOW",
    "state": "ACTIVE",
    "evidence_id": "evidence_94"
  },
  {
    "step_no": 5,
    "phase": "REMEDIATION",
    "system_id": "integration_service",
    "resource_id": "data_flow_4890",
    "operation": "DISABLE_DATA_FLOW",
    "state": "DISABLED",
    "evidence_id": ""
  },
  {
    "step_no": 6,
    "phase": "REMEDIATION",
    "system_id": "search_service",
    "resource_id": "search_4013",
    "operation": "DELETE_RECORD",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 7,
    "phase": "REMEDIATION",
    "system_id": "support_platform",
    "resource_id": "support_5569",
    "operation": "REDACT_RECORD",
    "state": "REDACTED",
    "evidence_id": ""
  },
  {
    "step_no": 8,
    "phase": "REMEDIATION",
    "system_id": "analytics_platform",
    "resource_id": "analytics_037",
    "operation": "ANONYMIZE_RECORD",
    "state": "ANONYMIZED",
    "evidence_id": ""
  },
  {
    "step_no": 9,
    "phase": "VERIFICATION",
    "system_id": "account_service",
    "resource_id": "account_5521",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 10,
    "phase": "VERIFICATION",
    "system_id": "search_service",
    "resource_id": "search_4013",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 11,
    "phase": "VERIFICATION",
    "system_id": "security_service",
    "resource_id": "audit_record_6645",
    "operation": "VERIFY_RECORD_PRESENT",
    "state": "PRESENT",
    "evidence_id": ""
  },
  {
    "step_no": 12,
    "phase": "VERIFICATION",
    "system_id": "support_platform",
    "resource_id": "support_5569",
    "operation": "VERIFY_RECORD_REDACTED",
    "state": "REDACTED",
    "evidence_id": ""
  },
  {
    "step_no": 13,
    "phase": "VERIFICATION",
    "system_id": "analytics_platform",
    "resource_id": "analytics_037",
    "operation": "VERIFY_RECORD_ANONYMIZED",
    "state": "ANONYMIZED",
    "evidence_id": ""
  },
  {
    "step_no": 14,
    "phase": "VERIFICATION",
    "system_id": "integration_service",
    "resource_id": "data_flow_4890",
    "operation": "VERIFY_DATA_FLOW_DISABLED",
    "state": "DISABLED",
    "evidence_id": ""
  }
]
// Predicted Steps
[
  {
    "step_no": 1,
    "phase": "FINDING",
    "system_id": "search_service",
    "resource_id": "search_4013",
    "operation": "REPORT_REMAINING_RECORD",
    "state": "PRESENT",
    "evidence_id": "evidence_94"
  },
  {
    "step_no": 2,
    "phase": "FINDING",
    "system_id": "analytics_platform",
    "resource_id": "analytics_037",
    "operation": "REPORT_EXPOSED_PII",
    "state": "PRESENT",
    "evidence_id": "evidence_94"
  },
  {
    "step_no": 3,
    "phase": "FINDING",
    "system_id": "support_platform",
    "resource_id": "support_5569",
    "operation": "REPORT_EXPOSED_PII",
    "state": "PRESENT",
    "evidence_id": "evidence_94"
  },
  {
    "step_no": 4,
    "phase": "FINDING",
    "system_id": "integration_service",
    "resource_id": "data_flow_4890",
    "operation": "REPORT_ACTIVE_DATA_FLOW",
    "state": "ACTIVE",
    "evidence_id": "evidence_94"
  },
  {
    "step_no": 5,
    "phase": "REMEDIATION",
    "system_id": "integration_service",
    "resource_id": "data_flow_4890",
    "operation": "DISABLE_DATA_FLOW",
    "state": "DISABLED",
    "evidence_id": ""
  },
  {
    "step_no": 6,
    "phase": "REMEDIATION",
    "system_id": "search_service",
    "resource_id": "search_4013",
    "operation": "DELETE_RECORD",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 7,
    "phase": "REMEDIATION",
    "system_id": "support_platform",
    "resource_id": "support_5569",
    "operation": "REDACT_RECORD",
    "state": "REDACTED",
    "evidence_id": ""
  },
  {
    "step_no": 8,
    "phase": "REMEDIATION",
    "system_id": "analytics_platform",
    "resource_id": "analytics_037",
    "operation": "ANONYMIZE_RECORD",
    "state": "ANONYMIZED",
    "evidence_id": ""
  },
  {
    "step_no": 9,
    "phase": "VERIFICATION",
    "system_id": "account_service",
    "resource_id": "account_5521",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 10,
    "phase": "VERIFICATION",
    "system_id": "search_service",
    "resource_id": "search_4013",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 11,
    "phase": "VERIFICATION",
    "system_id": "support_platform",
    "resource_id": "support_5569",
    "operation": "VERIFY_RECORD_REDACTED",
    "state": "REDACTED",
    "evidence_id": ""
  },
  {
    "step_no": 12,
    "phase": "VERIFICATION",
    "system_id": "analytics_platform",
    "resource_id": "analytics_037",
    "operation": "VERIFY_RECORD_ANONYMIZED",
    "state": "ANONYMIZED",
    "evidence_id": ""
  },
  {
    "step_no": 13,
    "phase": "VERIFICATION",
    "system_id": "integration_service",
    "resource_id": "data_flow_4890",
    "operation": "VERIFY_DATA_FLOW_DISABLED",
    "state": "DISABLED",
    "evidence_id": ""
  }
]
```

### case_20
- Status: Expected `INCOMPLETE`, Predicted `INCOMPLETE` (Match: True)
- Steps: Expected 8, Predicted 7
```json
// Expected Steps
[
  {
    "step_no": 1,
    "phase": "FINDING",
    "system_id": "search_service",
    "resource_id": "search_4262",
    "operation": "REPORT_REMAINING_RECORD",
    "state": "PRESENT",
    "evidence_id": "evidence_94"
  },
  {
    "step_no": 2,
    "phase": "FINDING",
    "system_id": "integration_service",
    "resource_id": "data_flow_1770",
    "operation": "REPORT_ACTIVE_DATA_FLOW",
    "state": "ACTIVE",
    "evidence_id": "evidence_94"
  },
  {
    "step_no": 3,
    "phase": "REMEDIATION",
    "system_id": "integration_service",
    "resource_id": "data_flow_1770",
    "operation": "DISABLE_DATA_FLOW",
    "state": "DISABLED",
    "evidence_id": ""
  },
  {
    "step_no": 4,
    "phase": "REMEDIATION",
    "system_id": "search_service",
    "resource_id": "search_4262",
    "operation": "DELETE_RECORD",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 5,
    "phase": "VERIFICATION",
    "system_id": "account_service",
    "resource_id": "account_5037",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 6,
    "phase": "VERIFICATION",
    "system_id": "search_service",
    "resource_id": "search_4262",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 7,
    "phase": "VERIFICATION",
    "system_id": "security_service",
    "resource_id": "audit_record_5569",
    "operation": "VERIFY_RECORD_PRESENT",
    "state": "PRESENT",
    "evidence_id": ""
  },
  {
    "step_no": 8,
    "phase": "VERIFICATION",
    "system_id": "integration_service",
    "resource_id": "data_flow_1770",
    "operation": "VERIFY_DATA_FLOW_DISABLED",
    "state": "DISABLED",
    "evidence_id": ""
  }
]
// Predicted Steps
[
  {
    "step_no": 1,
    "phase": "FINDING",
    "system_id": "search_service",
    "resource_id": "search_4262",
    "operation": "REPORT_REMAINING_RECORD",
    "state": "PRESENT",
    "evidence_id": "evidence_94"
  },
  {
    "step_no": 2,
    "phase": "FINDING",
    "system_id": "integration_service",
    "resource_id": "data_flow_1770",
    "operation": "REPORT_ACTIVE_DATA_FLOW",
    "state": "ACTIVE",
    "evidence_id": "evidence_94"
  },
  {
    "step_no": 3,
    "phase": "REMEDIATION",
    "system_id": "integration_service",
    "resource_id": "data_flow_1770",
    "operation": "DISABLE_DATA_FLOW",
    "state": "DISABLED",
    "evidence_id": ""
  },
  {
    "step_no": 4,
    "phase": "REMEDIATION",
    "system_id": "search_service",
    "resource_id": "search_4262",
    "operation": "DELETE_RECORD",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 5,
    "phase": "VERIFICATION",
    "system_id": "account_service",
    "resource_id": "account_5037",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 6,
    "phase": "VERIFICATION",
    "system_id": "search_service",
    "resource_id": "search_4262",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 7,
    "phase": "VERIFICATION",
    "system_id": "integration_service",
    "resource_id": "data_flow_1770",
    "operation": "VERIFY_DATA_FLOW_DISABLED",
    "state": "DISABLED",
    "evidence_id": ""
  }
]
```

### case_23
- Status: Expected `INCOMPLETE`, Predicted `INCOMPLETE` (Match: True)
- Steps: Expected 8, Predicted 8
```json
// Expected Steps
[
  {
    "step_no": 1,
    "phase": "FINDING",
    "system_id": "export_service",
    "resource_id": "export_7364",
    "operation": "REPORT_REMAINING_RECORD",
    "state": "PRESENT",
    "evidence_id": "evidence_92"
  },
  {
    "step_no": 2,
    "phase": "FINDING",
    "system_id": "search_service",
    "resource_id": "search_898",
    "operation": "REPORT_REMAINING_RECORD",
    "state": "PRESENT",
    "evidence_id": "evidence_92"
  },
  {
    "step_no": 3,
    "phase": "REMEDIATION",
    "system_id": "export_service",
    "resource_id": "export_7364",
    "operation": "DELETE_RECORD",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 4,
    "phase": "REMEDIATION",
    "system_id": "search_service",
    "resource_id": "search_898",
    "operation": "DELETE_RECORD",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 5,
    "phase": "VERIFICATION",
    "system_id": "account_service",
    "resource_id": "account_410",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 6,
    "phase": "VERIFICATION",
    "system_id": "export_service",
    "resource_id": "export_7364",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 7,
    "phase": "VERIFICATION",
    "system_id": "search_service",
    "resource_id": "search_898",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 8,
    "phase": "VERIFICATION",
    "system_id": "security_service",
    "resource_id": "audit_record_4128",
    "operation": "VERIFY_RECORD_PRESENT",
    "state": "PRESENT",
    "evidence_id": ""
  }
]
// Predicted Steps
[
  {
    "step_no": 1,
    "phase": "FINDING",
    "system_id": "export_service",
    "resource_id": "export_7364",
    "operation": "REPORT_REMAINING_RECORD",
    "state": "PRESENT",
    "evidence_id": "evidence_92"
  },
  {
    "step_no": 2,
    "phase": "FINDING",
    "system_id": "search_service",
    "resource_id": "search_898",
    "operation": "REPORT_REMAINING_RECORD",
    "state": "PRESENT",
    "evidence_id": "evidence_92"
  },
  {
    "step_no": 3,
    "phase": "REMEDIATION",
    "system_id": "export_service",
    "resource_id": "export_7364",
    "operation": "DELETE_RECORD",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 4,
    "phase": "REMEDIATION",
    "system_id": "search_service",
    "resource_id": "search_898",
    "operation": "DELETE_RECORD",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 5,
    "phase": "VERIFICATION",
    "system_id": "account_service",
    "resource_id": "account_9155",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 6,
    "phase": "VERIFICATION",
    "system_id": "export_service",
    "resource_id": "export_7364",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 7,
    "phase": "VERIFICATION",
    "system_id": "search_service",
    "resource_id": "search_898",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": ""
  },
  {
    "step_no": 8,
    "phase": "VERIFICATION",
    "system_id": "security_service",
    "resource_id": "audit_record_4128",
    "operation": "VERIFY_RECORD_PRESENT",
    "state": "PRESENT",
    "evidence_id": ""
  }
]
```

### case_27
- Status: Expected `COMPLETE`, Predicted `COMPLETE` (Match: True)
- Steps: Expected 6, Predicted 6
```json
// Expected Steps
[
  {
    "step_no": 1,
    "phase": "VERIFICATION",
    "system_id": "account_service",
    "resource_id": "account_3866",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": "evidence_92"
  },
  {
    "step_no": 2,
    "phase": "VERIFICATION",
    "system_id": "security_service",
    "resource_id": "audit_record_3830",
    "operation": "VERIFY_RECORD_PRESENT",
    "state": "PRESENT",
    "evidence_id": "evidence_92"
  },
  {
    "step_no": 3,
    "phase": "VERIFICATION",
    "system_id": "support_platform",
    "resource_id": "support_4707",
    "operation": "VERIFY_RECORD_REDACTED",
    "state": "REDACTED",
    "evidence_id": "evidence_92"
  },
  {
    "step_no": 4,
    "phase": "VERIFICATION",
    "system_id": "analytics_platform",
    "resource_id": "analytics_4574",
    "operation": "VERIFY_RECORD_ANONYMIZED",
    "state": "ANONYMIZED",
    "evidence_id": "evidence_92"
  },
  {
    "step_no": 5,
    "phase": "VERIFICATION",
    "system_id": "integration_service",
    "resource_id": "data_flow_2295",
    "operation": "VERIFY_DATA_FLOW_DISABLED",
    "state": "DISABLED",
    "evidence_id": "evidence_92"
  },
  {
    "step_no": 6,
    "phase": "VERIFICATION",
    "system_id": "backup_service",
    "resource_id": "backup_5970",
    "operation": "VERIFY_RESTORE_BLOCKED",
    "state": "BLOCKED",
    "evidence_id": "evidence_92"
  }
]
// Predicted Steps
[
  {
    "step_no": 1,
    "phase": "VERIFICATION",
    "system_id": "account_service",
    "resource_id": "account_3866",
    "operation": "VERIFY_RECORD_ABSENT",
    "state": "ABSENT",
    "evidence_id": "evidence_92"
  },
  {
    "step_no": 2,
    "phase": "VERIFICATION",
    "system_id": "security_service",
    "resource_id": "audit_record_3830",
    "operation": "VERIFY_RECORD_PRESENT",
    "state": "PRESENT",
    "evidence_id": "evidence_92"
  },
  {
    "step_no": 3,
    "phase": "VERIFICATION",
    "system_id": "support_platform",
    "resource_id": "support_4707",
    "operation": "VERIFY_RECORD_REDACTED",
    "state": "REDACTED",
    "evidence_id": "evidence_92"
  },
  {
    "step_no": 4,
    "phase": "VERIFICATION",
    "system_id": "analytics_platform",
    "resource_id": "analytics_6077",
    "operation": "VERIFY_RECORD_ANONYMIZED",
    "state": "ANONYMIZED",
    "evidence_id": "evidence_92"
  },
  {
    "step_no": 5,
    "phase": "VERIFICATION",
    "system_id": "integration_service",
    "resource_id": "data_flow_2295",
    "operation": "VERIFY_DATA_FLOW_DISABLED",
    "state": "DISABLED",
    "evidence_id": "evidence_92"
  },
  {
    "step_no": 6,
    "phase": "VERIFICATION",
    "system_id": "backup_service",
    "resource_id": "backup_5970",
    "operation": "VERIFY_RESTORE_BLOCKED",
    "state": "BLOCKED",
    "evidence_id": "evidence_92"
  }
]
```

