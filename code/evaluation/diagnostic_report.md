# Ghost Data Still Exists — Error Diagnostic Report

- **Evaluated**: `tmp_sample_baseline.csv` vs `dataset/sample_output.csv`
- **Total Discrepancies**: 4 / 32 cases
- **Case Status Accuracy**: 100.00%
- **Exact Step-Array Accuracy**: 87.50%
- **Field Fidelity**: 97.63%

## 1. Discrepancy Classification

- **Status Mismatches**: 0
- **Step Count Differences**: 2
- **Sequence / Precedence Violations**: 0
- **Citation / Temporal Horizon Violations**: 0

## 2. Detailed Per-Case Analysis

### Case `case_18`

- **Status**: Expected `INCOMPLETE`, Predicted `INCOMPLETE` (Match: `True`)
- **Step Counts**: Expected `14`, Predicted `13` (Missing: 1, Extra: 0)

**Missing Steps in Prediction**:
- `[VERIFICATION] security_service : audit_record_6645 | VERIFY_RECORD_PRESENT | PRESENT | cite: ''`

**Field Differences by Index**:
- Step Index 10:
  - `system_id`: expected `security_service`, predicted `support_platform`
  - `resource_id`: expected `audit_record_6645`, predicted `support_5569`
  - `operation`: expected `VERIFY_RECORD_PRESENT`, predicted `VERIFY_RECORD_REDACTED`
  - `state`: expected `PRESENT`, predicted `REDACTED`
- Step Index 11:
  - `system_id`: expected `support_platform`, predicted `analytics_platform`
  - `resource_id`: expected `support_5569`, predicted `analytics_037`
  - `operation`: expected `VERIFY_RECORD_REDACTED`, predicted `VERIFY_RECORD_ANONYMIZED`
  - `state`: expected `REDACTED`, predicted `ANONYMIZED`
- Step Index 12:
  - `system_id`: expected `analytics_platform`, predicted `integration_service`
  - `resource_id`: expected `analytics_037`, predicted `data_flow_4890`
  - `operation`: expected `VERIFY_RECORD_ANONYMIZED`, predicted `VERIFY_DATA_FLOW_DISABLED`
  - `state`: expected `ANONYMIZED`, predicted `DISABLED`
- Step Index 13:
  - `step_no`: expected `14`, predicted `None`
  - `phase`: expected `VERIFICATION`, predicted `None`
  - `system_id`: expected `integration_service`, predicted `None`
  - `resource_id`: expected `data_flow_4890`, predicted `None`
  - `operation`: expected `VERIFY_DATA_FLOW_DISABLED`, predicted `None`
  - `state`: expected `DISABLED`, predicted `None`
  - `evidence_id`: expected ``, predicted `None`

---

### Case `case_20`

- **Status**: Expected `INCOMPLETE`, Predicted `INCOMPLETE` (Match: `True`)
- **Step Counts**: Expected `8`, Predicted `7` (Missing: 1, Extra: 0)

**Missing Steps in Prediction**:
- `[VERIFICATION] security_service : audit_record_5569 | VERIFY_RECORD_PRESENT | PRESENT | cite: ''`

**Field Differences by Index**:
- Step Index 6:
  - `system_id`: expected `security_service`, predicted `integration_service`
  - `resource_id`: expected `audit_record_5569`, predicted `data_flow_1770`
  - `operation`: expected `VERIFY_RECORD_PRESENT`, predicted `VERIFY_DATA_FLOW_DISABLED`
  - `state`: expected `PRESENT`, predicted `DISABLED`
- Step Index 7:
  - `step_no`: expected `8`, predicted `None`
  - `phase`: expected `VERIFICATION`, predicted `None`
  - `system_id`: expected `integration_service`, predicted `None`
  - `resource_id`: expected `data_flow_1770`, predicted `None`
  - `operation`: expected `VERIFY_DATA_FLOW_DISABLED`, predicted `None`
  - `state`: expected `DISABLED`, predicted `None`
  - `evidence_id`: expected ``, predicted `None`

---

### Case `case_23`

- **Status**: Expected `INCOMPLETE`, Predicted `INCOMPLETE` (Match: `True`)
- **Step Counts**: Expected `8`, Predicted `8` (Missing: 1, Extra: 1)

**Missing Steps in Prediction**:
- `[VERIFICATION] account_service : account_410 | VERIFY_RECORD_ABSENT | ABSENT | cite: ''`

**Extra Steps in Prediction**:
- `[VERIFICATION] account_service : account_9155 | VERIFY_RECORD_ABSENT | ABSENT | cite: ''`

**Field Differences by Index**:
- Step Index 4:
  - `resource_id`: expected `account_410`, predicted `account_9155`

---

### Case `case_27`

- **Status**: Expected `COMPLETE`, Predicted `COMPLETE` (Match: `True`)
- **Step Counts**: Expected `6`, Predicted `6` (Missing: 1, Extra: 1)

**Missing Steps in Prediction**:
- `[VERIFICATION] analytics_platform : analytics_4574 | VERIFY_RECORD_ANONYMIZED | ANONYMIZED | cite: 'evidence_92'`

**Extra Steps in Prediction**:
- `[VERIFICATION] analytics_platform : analytics_6077 | VERIFY_RECORD_ANONYMIZED | ANONYMIZED | cite: 'evidence_92'`

**Field Differences by Index**:
- Step Index 3:
  - `resource_id`: expected `analytics_4574`, predicted `analytics_6077`

---

