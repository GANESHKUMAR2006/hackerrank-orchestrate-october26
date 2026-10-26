import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Overview } from '../components/Overview';
import { CaseExplorer } from '../components/CaseExplorer';
import { CaseDetailModal } from '../components/CaseDetailModal';
import { ValidationBanner } from '../components/ValidationBanner';
import { calculateStats } from '../utils/stats';
import type { AuditCase, ValidationResult } from '../types';

const mockCases: AuditCase[] = [
  {
    case_id: 'case_33',
    deletion_status: 'INCOMPLETE',
    steps: [
      {
        step_no: 1,
        phase: 'FINDING',
        system_id: 'account_service',
        resource_id: 'account_hist',
        operation: 'REPORT_REMAINING_RECORD',
        state: 'PRESENT',
        evidence_id: 'evidence_18',
      },
      {
        step_no: 2,
        phase: 'REMEDIATION',
        system_id: 'account_service',
        resource_id: 'account_hist',
        operation: 'DELETE_RECORD',
        state: 'ABSENT',
        evidence_id: '',
      },
      {
        step_no: 3,
        phase: 'VERIFICATION',
        system_id: 'account_service',
        resource_id: 'account_hist',
        operation: 'VERIFY_RECORD_ABSENT',
        state: 'ABSENT',
        evidence_id: '',
      },
    ],
    raw_steps_json: '[]',
    line_number: 2,
    findings_count: 1,
    remediations_count: 1,
    verifications_count: 1,
  },
  {
    case_id: 'case_34',
    deletion_status: 'COMPLETE',
    steps: [
      {
        step_no: 1,
        phase: 'VERIFICATION',
        system_id: 'account_service',
        resource_id: 'account_5762',
        operation: 'VERIFY_RECORD_ABSENT',
        state: 'ABSENT',
        evidence_id: 'evidence_01',
      },
    ],
    raw_steps_json: '[]',
    line_number: 3,
    findings_count: 0,
    remediations_count: 0,
    verifications_count: 1,
  },
  {
    case_id: 'case_35',
    deletion_status: 'NOT_APPLICABLE',
    steps: [],
    raw_steps_json: '[]',
    line_number: 4,
    findings_count: 0,
    remediations_count: 0,
    verifications_count: 0,
  },
];

describe('Overview Component', () => {
  it('renders total counts and percentage distributions accurately', () => {
    const stats = calculateStats(mockCases);
    render(<Overview stats={stats} />);

    expect(screen.getByText('3')).toBeInTheDocument(); // Total cases
    expect(screen.getByText('Complete')).toBeInTheDocument();
    expect(screen.getByText('Incomplete')).toBeInTheDocument();
    expect(screen.getByText('Not Applicable')).toBeInTheDocument();
    expect(screen.getByText(/Point-in-Time Audit Classification Notice/i)).toBeInTheDocument();
  });
});

describe('CaseExplorer Component', () => {
  it('renders case list and handles search and selection', () => {
    const onSelect = vi.fn();
    const onFilterStatus = vi.fn();

    render(
      <CaseExplorer
        cases={mockCases}
        onSelectCase={onSelect}
        statusFilter="ALL"
        onStatusFilterChange={onFilterStatus}
      />
    );

    expect(screen.getByText('case_33')).toBeInTheDocument();
    expect(screen.getByText('case_34')).toBeInTheDocument();
    expect(screen.getByText('case_35')).toBeInTheDocument();

    // Search for case_33
    const searchInput = screen.getByPlaceholderText(/Search by case ID/i);
    fireEvent.change(searchInput, { target: { value: 'case_33' } });

    expect(screen.getByText('case_33')).toBeInTheDocument();
    expect(screen.queryByText('case_34')).not.toBeInTheDocument();

    // Click case_33
    fireEvent.click(screen.getByText('case_33'));
    expect(onSelect).toHaveBeenCalledWith(mockCases[0]);
  });
});

describe('CaseDetailModal Component', () => {
  it('renders steps and distinguishes verified evidence from proposed remediation', () => {
    const onClose = vi.fn();
    render(<CaseDetailModal auditCase={mockCases[0]} onClose={onClose} />);

    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('case_33');
    expect(screen.getByText('INCOMPLETE')).toBeInTheDocument();

    // Check evidence-backed finding step
    expect(screen.getByText(/Verified Evidence Citation:/i)).toBeInTheDocument();
    expect(screen.getByText('evidence_18')).toBeInTheDocument();

    // Check proposed remediation warning & empty citation label
    expect(screen.getByText(/Planned Remediation Actions/i)).toBeInTheDocument();
    expect(
      screen.getAllByText(/Proposed Action — Empty Citation/i).length
    ).toBeGreaterThan(0);
  });

  it('renders NOT_APPLICABLE empty state appropriately', () => {
    const onClose = vi.fn();
    render(<CaseDetailModal auditCase={mockCases[2]} onClose={onClose} />);

    expect(screen.getByText(/Non-Deletion Request \(Empty Steps Array\)/i)).toBeInTheDocument();
  });
});

describe('ValidationBanner Component', () => {
  it('shows green success state for clean dataset', () => {
    const valid: ValidationResult = {
      cases: mockCases,
      warnings: [],
      errors: [],
      total_rows: 3,
      is_valid_header: true,
      filename: 'output.csv',
    };
    render(<ValidationBanner validation={valid} />);
    expect(screen.getByText(/Schema & Integrity Validated/i)).toBeInTheDocument();
  });

  it('shows warnings list when malformed rows exist', () => {
    const withWarn: ValidationResult = {
      cases: mockCases,
      warnings: ['Line 5: Malformed JSON in steps_json.'],
      errors: [],
      total_rows: 3,
      is_valid_header: true,
      filename: 'dirty_output.csv',
    };
    render(<ValidationBanner validation={withWarn} />);
    expect(screen.getByText(/1 Parsing \/ Integrity Notice/i)).toBeInTheDocument();
  });
});
