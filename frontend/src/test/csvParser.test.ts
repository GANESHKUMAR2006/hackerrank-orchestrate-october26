import { describe, it, expect } from 'vitest';
import { parseCSVRows, parseOutputCSV } from '../utils/csvParser';
import { calculateStats } from '../utils/stats';

describe('parseCSVRows', () => {
  it('parses basic CSV lines correctly', () => {
    const csv = 'col1,col2,col3\nval1,val2,val3\nval4,val5,val6';
    const rows = parseCSVRows(csv);
    expect(rows).toEqual([
      ['col1', 'col2', 'col3'],
      ['val1', 'val2', 'val3'],
      ['val4', 'val5', 'val6'],
    ]);
  });

  it('handles quoted fields containing commas', () => {
    const csv = 'case_id,deletion_status,steps_json\ncase_01,COMPLETE,"[{""step_no"":1,""phase"":""VERIFICATION""}]"';
    const rows = parseCSVRows(csv);
    expect(rows.length).toBe(2);
    expect(rows[1][0]).toBe('case_01');
    expect(rows[1][1]).toBe('COMPLETE');
    expect(rows[1][2]).toBe('[{"step_no":1,"phase":"VERIFICATION"}]');
  });

  it('handles Windows CRLF and trailing newlines', () => {
    const csv = "case_id,deletion_status,steps_json\r\ncase_01,NOT_APPLICABLE,[]\r\n";
    const rows = parseCSVRows(csv);
    expect(rows.length).toBe(2);
    expect(rows[1]).toEqual(['case_01', 'NOT_APPLICABLE', '[]']);
  });
});

describe('parseOutputCSV', () => {
  it('parses valid output CSV and extracts typed cases', () => {
    const csv = 'case_id,deletion_status,steps_json\n' +
      'case_01,NOT_APPLICABLE,[]\n' +
      'case_02,COMPLETE,"[{""step_no"":1,""phase"":""VERIFICATION"",""system_id"":""account_service"",""resource_id"":""account_001"",""operation"":""VERIFY_RECORD_ABSENT"",""state"":""ABSENT"",""evidence_id"":""evidence_92""}]"\n' +
      'case_03,INCOMPLETE,"[{""step_no"":1,""phase"":""FINDING"",""system_id"":""search_service"",""resource_id"":""search_001"",""operation"":""REPORT_REMAINING_RECORD"",""state"":""PRESENT"",""evidence_id"":""evidence_01""},{""step_no"":2,""phase"":""REMEDIATION"",""system_id"":""search_service"",""resource_id"":""search_001"",""operation"":""DELETE_RECORD"",""state"":""ABSENT"",""evidence_id"":""""},{""step_no"":3,""phase"":""VERIFICATION"",""system_id"":""search_service"",""resource_id"":""search_001"",""operation"":""VERIFY_RECORD_ABSENT"",""state"":""ABSENT"",""evidence_id"":""""}]"';

    const result = parseOutputCSV(csv, 'test_output.csv');
    expect(result.errors.length).toBe(0);
    expect(result.cases.length).toBe(3);
    expect(result.is_valid_header).toBe(true);

    // Case 01
    expect(result.cases[0].case_id).toBe('case_01');
    expect(result.cases[0].deletion_status).toBe('NOT_APPLICABLE');
    expect(result.cases[0].steps).toEqual([]);

    // Case 02
    expect(result.cases[1].case_id).toBe('case_02');
    expect(result.cases[1].deletion_status).toBe('COMPLETE');
    expect(result.cases[1].steps.length).toBe(1);
    expect(result.cases[1].steps[0].evidence_id).toBe('evidence_92');

    // Case 03
    expect(result.cases[2].case_id).toBe('case_03');
    expect(result.cases[2].deletion_status).toBe('INCOMPLETE');
    expect(result.cases[2].findings_count).toBe(1);
    expect(result.cases[2].remediations_count).toBe(1);
    expect(result.cases[2].verifications_count).toBe(1);
  });

  it('detects invalid header', () => {
    const csv = 'wrong_id,wrong_status,steps\ncase_01,COMPLETE,[]';
    const result = parseOutputCSV(csv);
    expect(result.is_valid_header).toBe(false);
    expect(result.errors.length).toBeGreaterThan(0);
  });

  it('detects malformed JSON and reports structured warning', () => {
    const csv = 'case_id,deletion_status,steps_json\ncase_01,COMPLETE,{not_an_array}';
    const result = parseOutputCSV(csv);
    expect(result.cases.length).toBe(1);
    expect(result.warnings.some((w) => w.includes('Malformed JSON'))).toBe(true);
  });

  it('flags NOT_APPLICABLE cases with non-empty steps', () => {
    const csv = 'case_id,deletion_status,steps_json\ncase_01,NOT_APPLICABLE,"[{""step_no"":1,""phase"":""VERIFICATION""}]"';
    const result = parseOutputCSV(csv);
    expect(result.warnings.some((w) => w.includes('NOT_APPLICABLE status must have empty steps array'))).toBe(true);
  });
});

describe('calculateStats', () => {
  it('computes accurate counts and percentages', () => {
    const cases = [
      {
        case_id: 'case_01',
        deletion_status: 'COMPLETE' as const,
        steps: [
          { step_no: 1, phase: 'VERIFICATION' as const, system_id: 's1', resource_id: 'r1', operation: 'op', state: 'st', evidence_id: 'e1' },
        ],
        raw_steps_json: '[]',
        line_number: 2,
        findings_count: 0,
        remediations_count: 0,
        verifications_count: 1,
      },
      {
        case_id: 'case_02',
        deletion_status: 'INCOMPLETE' as const,
        steps: [
          { step_no: 1, phase: 'FINDING' as const, system_id: 's1', resource_id: 'r1', operation: 'op', state: 'st', evidence_id: 'e1' },
          { step_no: 2, phase: 'REMEDIATION' as const, system_id: 's1', resource_id: 'r1', operation: 'op', state: 'st', evidence_id: '' },
          { step_no: 3, phase: 'VERIFICATION' as const, system_id: 's1', resource_id: 'r1', operation: 'op', state: 'st', evidence_id: '' },
        ],
        raw_steps_json: '[]',
        line_number: 3,
        findings_count: 1,
        remediations_count: 1,
        verifications_count: 1,
      },
      {
        case_id: 'case_03',
        deletion_status: 'NOT_APPLICABLE' as const,
        steps: [],
        raw_steps_json: '[]',
        line_number: 4,
        findings_count: 0,
        remediations_count: 0,
        verifications_count: 0,
      },
    ];

    const stats = calculateStats(cases);
    expect(stats.total).toBe(3);
    expect(stats.complete).toBe(1);
    expect(stats.incomplete).toBe(1);
    expect(stats.not_applicable).toBe(1);
    expect(stats.complete_pct).toBeCloseTo(33.33, 1);
    expect(stats.total_steps).toBe(4);
    expect(stats.total_findings).toBe(1);
    expect(stats.total_remediations).toBe(1);
    expect(stats.total_verifications).toBe(2);
    expect(stats.avg_steps_per_case).toBeCloseTo(1.33, 1);
  });

  it('handles empty cases array gracefully', () => {
    const stats = calculateStats([]);
    expect(stats.total).toBe(0);
    expect(stats.complete).toBe(0);
    expect(stats.avg_steps_per_case).toBe(0);
  });
});
