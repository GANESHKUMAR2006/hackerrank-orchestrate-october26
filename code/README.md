# Ghost Data Still Exists — Architecture & Solution Guide

This document describes the architecture, component interfaces, assumptions, operational contracts, and run commands for the HackerRank Orchestrate October 2026 solution: **Ghost Data Still Exists**.

---

## 1. System Architecture

The solution implements an end-to-end, multi-stage audit pipeline designed to detect "ghost data," identify replication drift, discover active data recreation risks, apply data retention/deletion policies, and produce deterministic remediation plans.

```
                              [ deletion_requests.csv ]
                                         │
                                         ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ 1. Request Intent Classifier & Gatekeeper                                   │
 │    - Multi-language intent parsing (English, French, Spanish, Japanese, etc)│
 │    - Filters out access, correction, export, marketing opt-out, inquiries   │
 │    - Directs non-deletion requests to NOT_APPLICABLE (steps_json = [])      │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │ (Authorized Deletion)
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ 2. Identity Graph Resolver                                                  │
 │    - Matches requested email against user_identities.csv & user_audit_log   │
 │    - Recovers current & historical user_id, emails, phones, names, hashes   │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ 3. Multi-Format Evidence Ingestion & Temporal Indexer                       │
 │    - Filters evidence by cutoff: captured_at <= audit_at                   │
 │    - SQLite Snapshot Engine (.sql: primary, failover, reporting, regional)  │
 │    - Structured Record Parser (.json: bundles, exports, manifests)          │
 │    - Service Log Analyzer (.log: key-value pairs, trace IDs, status codes)  │
 │    - Document Extractor (.pdf: invoices, statements, registers via PyMuPDF) │
 │    - Handover & Text Parser (.txt)                                          │
 │    - Admin Console Vision / Structured Transcripts (.png)                   │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ 4. Deletion State & Drift Auditor                                           │
 │    - Audits account service, search indexes, analytics, support, exports    │
 │    - Identifies replication drift between primary and secondary replicas    │
 │    - Detects active connectors / data flows (integration_service)           │
 │    - Identifies unblocked restore risks (backup_service)                    │
 │    - Validates tombstones (verifying stable user_id retained, PII redacted) │
 │    - Validates retention obligations (security audits, legal holds, orders) │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ 5. Policy Planner & Remediation Synthesizer                                 │
 │    - Applies 15 rules from deletion_rules.csv                               │
 │    - Synthesizes FINDING steps (backed by file_id, activity_id, audit_id)   │
 │    - Orders REMEDIATION steps (disable flows & block restores first!)       │
 │    - Generates VERIFICATION checks (evidence-backed for COMPLETE cases)     │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ 6. Deterministic Formatter & Canonical Serializer                           │
 │    - Enforces 5-level sorting hierarchy and consecutive step numbering      │
 │    - Outputs valid, compact JSON array for steps_json                       │
 │    - Emits output.csv with exact 518 cases sorted by case_id                │
 └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Modules and Interfaces

### 2.1 `code/models.py`
Data structures using Python dataclasses / Pydantic models:
- `DeletionRequest`: `case_id`, `email`, `requested_at`, `reported_status`, `reported_at`, `audit_at`, `request_text`
- `UserIdentityGraph`: `user_id`, `names: set[str]`, `emails: set[str]`, `phones: set[str]`, `email_hashes: set[str]`
- `AuditStep`: `step_no: int`, `phase: str`, `system_id: str`, `resource_id: str`, `operation: str`, `state: str`, `evidence_id: str`
- `CaseResult`: `case_id: str`, `deletion_status: str`, `steps: list[AuditStep]`

### 2.2 `code/classifier.py` (`RequestClassifier`)
- **Interface**: `classify_intent(request_text: str) -> bool`
- **Functionality**: Returns `True` if `request_text` authorizes account/personal data deletion; returns `False` if the request is for access/inspection, rectification, export only, marketing unsubscribe, or general inquiry.

### 2.3 `code/identity.py` (`IdentityResolver`)
- **Interface**: `resolve_identity(email: str) -> Optional[UserIdentityGraph]`
- **Functionality**: Cross-references `email` with `dataset/user_identities.csv` and historical entries in `dataset/user_audit_log.csv`. Aggregates all alias emails, previous phone numbers, full names, and SHA-256 hashes linked to the user.

### 2.4 `code/evidence/` (Parsers)
- `sql_parser.py`: Executes in-memory SQLite instances or parses table statements to inspect primary vs failover/regional replica drift.
- `json_parser.py`: Ingests customer data snapshot bundles, service exports, and manifests.
- `log_parser.py`: Ingests key-value log formats, HTTP status codes (200 hit vs 404 not found), and connector state.
- `document_parser.py`: Uses `pymupdf` to extract text, tables, and references from PDFs (statements, address corrections, legal retention registers).
- `image_catalog.py`: Structured data extracts for the 11 console screenshot artifacts.
- `temporal_filter.py`: Enforces that no evidence with `captured_at > audit_at` is evaluated or cited.

### 2.5 `code/auditor.py` (`DeletionAuditor`)
- **Interface**: `audit_case(request: DeletionRequest, identity: UserIdentityGraph) -> CaseResult`
- **Functionality**:
  1. Searches evidence captured on or before `audit_at` for user identifiers.
  2. Evaluates state of records in:
     - `account_service` (primary profile, replicas)
     - `search_service` (search index entries)
     - `analytics_platform` (identifiable vs anonymized records)
     - `support_platform` (attachments vs messages)
     - `integration_service` (active vs disabled data flows)
     - `backup_service` (active vs blocked restore policies)
     - `security_service` (retained security audit logs)
     - `identity_service` (tombstone records: direct PII removed vs exposed)
     - `export_service` (download archives)
  3. Maps findings and compliant states to `deletion_rules.csv`.

### 2.6 `code/planner.py` (`StepPlanner`)
- **Interface**: `build_steps(findings: list[Finding], verifications: list[Verification]) -> list[AuditStep]`
- **Functionality**:
  - Enforces phase ordering: `FINDING` -> `REMEDIATION` -> `VERIFICATION`.
  - Enforces remediation order: disable data flows and block restores before record deletions/redactions.
  - Generates post-remediation verification checks for `INCOMPLETE` cases with empty `evidence_id: ""`.
  - Preserves evidence IDs for `COMPLETE` verification steps.
  - Sorts ties by `system_id` ascending, then `resource_id` ascending.
  - Assigns consecutive `step_no` starting at 1.

### 2.7 `code/evaluation/` (`EvaluationHarness`)
- `main.py`: Evaluates predictions against ground truth (e.g. `sample_output.csv`).
- Produces:
  - `code/evaluation/evaluation_report.md`
  - `code/evaluation/usage_report.md`

---

## 3. Assumptions & Operational Contracts

1. **Temporal Horizon (`audit_at`)**:
   Any activity, log, snapshot, or evidence file with timestamp strictly greater than `audit_at` is considered future information and must NOT influence the decision or be cited as evidence.
2. **Untrusted Claims**:
   The `reported_status` in `deletion_requests.csv` and `reported_result` in `system_activity.csv` are considered claims by existing services, not truth. Ground truth is derived exclusively from evidence artifacts.
3. **Evidence References**:
   Only participant-visible IDs may be cited in `evidence_id`:
   - A valid `file_id` from `evidence_files.csv` (e.g., `evidence_01`, `evidence_54`)
   - A valid `activity_id` from `system_activity.csv`
   - A valid `audit_id` from `user_audit_log.csv`
   Proposed remediation and post-remediation verification steps in `INCOMPLETE` cases must have `evidence_id: ""`.
4. **Account Tombstones**:
   An account tombstone (`rule_15`) is valid only when direct identifiers (`name`, `email`, `phone`, `email_hash`) are redacted while preserving the stable internal `user_id` so retained audit/tax records remain referentially intact. If direct identifiers are present, it is a policy violation (`REPORT_EXPOSED_PII`).
5. **Deterministic Serialization**:
   The output CSV must contain exactly 518 data rows plus header, sorted by `case_id`. JSON in `steps_json` must be strictly formatted with valid syntax and no trailing commas.

---

## 4. Run Commands

### 4.1 Environment Setup
```bash
# Verify Python 3.10+
python --version

# Install dependencies if in a new virtual environment
pip install pymupdf pytest pydantic
```

### 4.2 Run Test Suite
```bash
pytest code/tests/ -v
```

### 4.3 Run Evaluation on Public Samples (32 Cases)
```bash
python code/evaluation/main.py --mode sample
```

### 4.4 Run Full Solution (518 Cases)
```bash
python code/main.py
```
This produces `output.csv` at the repository root.

### 4.5 Package for Submission
```powershell
# Windows PowerShell packaging:
Compress-Archive -Path README.md, code -DestinationPath code.zip -Force
```
```bash
# Linux / macOS packaging:
zip -r code.zip README.md code -x "*/__pycache__/*" "*/.venv/*" "*/venv/*" "*/.git/*"
```
