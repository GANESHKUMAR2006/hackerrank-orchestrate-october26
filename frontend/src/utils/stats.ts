import type { AuditCase, OverviewStats } from '../types';

export function calculateStats(cases: AuditCase[]): OverviewStats {
  const total = cases.length;
  if (total === 0) {
    return {
      total: 0,
      complete: 0,
      incomplete: 0,
      not_applicable: 0,
      complete_pct: 0,
      incomplete_pct: 0,
      not_applicable_pct: 0,
      total_steps: 0,
      total_findings: 0,
      total_remediations: 0,
      total_verifications: 0,
      avg_steps_per_case: 0,
    };
  }

  let complete = 0;
  let incomplete = 0;
  let not_applicable = 0;
  let total_steps = 0;
  let total_findings = 0;
  let total_remediations = 0;
  let total_verifications = 0;

  for (const c of cases) {
    if (c.deletion_status === 'COMPLETE') {
      complete++;
    } else if (c.deletion_status === 'INCOMPLETE') {
      incomplete++;
    } else if (c.deletion_status === 'NOT_APPLICABLE') {
      not_applicable++;
    }

    total_steps += c.steps.length;
    total_findings += c.findings_count;
    total_remediations += c.remediations_count;
    total_verifications += c.verifications_count;
  }

  return {
    total,
    complete,
    incomplete,
    not_applicable,
    complete_pct: (complete / total) * 100,
    incomplete_pct: (incomplete / total) * 100,
    not_applicable_pct: (not_applicable / total) * 100,
    total_steps,
    total_findings,
    total_remediations,
    total_verifications,
    avg_steps_per_case: total_steps / total,
  };
}
