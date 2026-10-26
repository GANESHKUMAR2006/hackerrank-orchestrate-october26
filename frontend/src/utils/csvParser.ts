import type { AuditCase, AuditStep, DeletionStatus, Phase, ValidationResult } from '../types';

/**
 * Standard RFC 4180 CSV line tokenizer supporting quotes, escaped quotes, and newlines.
 */
export function parseCSVRows(csvText: string): string[][] {
  // Strip BOM if present
  const cleanText = csvText.replace(/^\uFEFF/, '');
  const rows: string[][] = [];
  let currentRow: string[] = [];
  let currentField = '';
  let inQuotes = false;

  for (let i = 0; i < cleanText.length; i++) {
    const char = cleanText[i];
    const nextChar = i + 1 < cleanText.length ? cleanText[i + 1] : '';

    if (inQuotes) {
      if (char === '"') {
        if (nextChar === '"') {
          // Escaped quote: "" -> "
          currentField += '"';
          i++;
        } else {
          // End of quote
          inQuotes = false;
        }
      } else {
        currentField += char;
      }
    } else {
      if (char === '"') {
        inQuotes = true;
      } else if (char === ',') {
        currentRow.push(currentField);
        currentField = '';
      } else if (char === '\r') {
        if (nextChar === '\n') {
          i++;
        }
        currentRow.push(currentField);
        rows.push(currentRow);
        currentRow = [];
        currentField = '';
      } else if (char === '\n') {
        currentRow.push(currentField);
        rows.push(currentRow);
        currentRow = [];
        currentField = '';
      } else {
        currentField += char;
      }
    }
  }

  // Push final field/row if text doesn't end with newline
  if (currentField.length > 0 || currentRow.length > 0) {
    currentRow.push(currentField);
    rows.push(currentRow);
  }

  // Filter out any trailing empty rows
  return rows.filter((r) => r.length > 1 || (r.length === 1 && r[0].trim() !== ''));
}

/**
 * Validate and parse output.csv into typed AuditCase records.
 */
export function parseOutputCSV(csvText: string, filename: string = 'output.csv'): ValidationResult {
  const warnings: string[] = [];
  const errors: string[] = [];
  const cases: AuditCase[] = [];

  const rawRows = parseCSVRows(csvText);

  if (rawRows.length === 0) {
    errors.push('File is empty.');
    return {
      cases: [],
      warnings,
      errors,
      total_rows: 0,
      is_valid_header: false,
      filename,
    };
  }

  const header = rawRows[0].map((h) => h.trim());
  const expectedHeader = ['case_id', 'deletion_status', 'steps_json'];
  const isValidHeader =
    header.length >= 3 &&
    header[0] === expectedHeader[0] &&
    header[1] === expectedHeader[1] &&
    header[2] === expectedHeader[2];

  if (!isValidHeader) {
    errors.push(
      `Invalid CSV header: expected [case_id,deletion_status,steps_json], found [${header.join(',')}]`
    );
  }

  const allowedStatuses = new Set<string>(['COMPLETE', 'INCOMPLETE', 'NOT_APPLICABLE']);
  const allowedPhases = new Set<string>(['FINDING', 'REMEDIATION', 'VERIFICATION']);

  for (let rowIndex = 1; rowIndex < rawRows.length; rowIndex++) {
    const row = rawRows[rowIndex];
    const lineNum = rowIndex + 1;

    if (row.length < 3) {
      warnings.push(`Line ${lineNum}: Row has fewer than 3 columns (found ${row.length}).`);
      continue;
    }

    const caseId = row[0].trim();
    const rawStatus = row[1].trim().toUpperCase();
    const rawStepsJson = row[2].trim();

    if (!caseId) {
      warnings.push(`Line ${lineNum}: Missing case_id.`);
      continue;
    }

    if (!allowedStatuses.has(rawStatus)) {
      warnings.push(
        `Line ${lineNum} (${caseId}): Invalid status "${rawStatus}". Must be COMPLETE, INCOMPLETE, or NOT_APPLICABLE.`
      );
    }
    const deletionStatus = (allowedStatuses.has(rawStatus) ? rawStatus : 'INCOMPLETE') as DeletionStatus;

    let steps: AuditStep[] = [];
    try {
      const parsed = JSON.parse(rawStepsJson);
      if (!Array.isArray(parsed)) {
        warnings.push(`Line ${lineNum} (${caseId}): steps_json is not an array.`);
      } else {
        steps = parsed.map((item, idx) => {
          const stepNo = typeof item.step_no === 'number' ? item.step_no : idx + 1;
          const phase = (allowedPhases.has(item.phase) ? item.phase : 'VERIFICATION') as Phase;
          const systemId = item.system_id ? String(item.system_id).trim() : 'unknown_system';
          const resourceId = item.resource_id ? String(item.resource_id).trim() : 'unknown_resource';
          const operation = item.operation ? String(item.operation).trim() : 'UNKNOWN_OP';
          const state = item.state ? String(item.state).trim() : 'UNKNOWN';
          const evidenceId = item.evidence_id ? String(item.evidence_id).trim() : '';

          return {
            step_no: stepNo,
            phase,
            system_id: systemId,
            resource_id: resourceId,
            operation,
            state,
            evidence_id: evidenceId,
          };
        });
      }
    } catch {
      warnings.push(`Line ${lineNum} (${caseId}): Malformed JSON in steps_json.`);
    }

    // Special validation checks for statuses
    if (deletionStatus === 'NOT_APPLICABLE' && steps.length > 0) {
      warnings.push(`Line ${lineNum} (${caseId}): NOT_APPLICABLE status must have empty steps array, found ${steps.length} steps.`);
    }
    if (deletionStatus === 'COMPLETE' && steps.some((s) => s.phase !== 'VERIFICATION')) {
      warnings.push(`Line ${lineNum} (${caseId}): COMPLETE status should only contain VERIFICATION steps.`);
    }

    const findingsCount = steps.filter((s) => s.phase === 'FINDING').length;
    const remediationsCount = steps.filter((s) => s.phase === 'REMEDIATION').length;
    const verificationsCount = steps.filter((s) => s.phase === 'VERIFICATION').length;

    cases.push({
      case_id: caseId,
      deletion_status: deletionStatus,
      steps,
      raw_steps_json: rawStepsJson,
      line_number: lineNum,
      findings_count: findingsCount,
      remediations_count: remediationsCount,
      verifications_count: verificationsCount,
    });
  }

  return {
    cases,
    warnings,
    errors,
    total_rows: cases.length,
    is_valid_header: isValidHeader,
    filename,
  };
}
