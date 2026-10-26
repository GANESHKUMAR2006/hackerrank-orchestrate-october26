export type DeletionStatus = 'COMPLETE' | 'INCOMPLETE' | 'NOT_APPLICABLE';

export type Phase = 'FINDING' | 'REMEDIATION' | 'VERIFICATION';

export interface AuditStep {
  step_no: number;
  phase: Phase;
  system_id: string;
  resource_id: string;
  operation: string;
  state: string;
  evidence_id: string;
}

export interface AuditCase {
  case_id: string;
  deletion_status: DeletionStatus;
  steps: AuditStep[];
  raw_steps_json: string;
  line_number: number;
  findings_count: number;
  remediations_count: number;
  verifications_count: number;
  warning?: string;
}

export interface ValidationResult {
  cases: AuditCase[];
  warnings: string[];
  errors: string[];
  total_rows: number;
  is_valid_header: boolean;
  filename: string;
}

export interface OverviewStats {
  total: number;
  complete: number;
  incomplete: number;
  not_applicable: number;
  complete_pct: number;
  incomplete_pct: number;
  not_applicable_pct: number;
  total_steps: number;
  total_findings: number;
  total_remediations: number;
  total_verifications: number;
  avg_steps_per_case: number;
}
