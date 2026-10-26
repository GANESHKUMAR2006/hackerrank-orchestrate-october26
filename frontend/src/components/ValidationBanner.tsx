import React, { useState } from 'react';
import { AlertTriangle, AlertCircle, CheckCircle2, ChevronDown, ChevronUp } from 'lucide-react';
import type { ValidationResult } from '../types';

interface ValidationBannerProps {
  validation: ValidationResult;
}

export const ValidationBanner: React.FC<ValidationBannerProps> = ({ validation }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const hasErrors = validation.errors.length > 0;
  const hasWarnings = validation.warnings.length > 0;

  if (!hasErrors && !hasWarnings) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.6rem',
          backgroundColor: 'var(--status-complete-bg)',
          border: '1px solid var(--status-complete-border)',
          color: 'var(--status-complete)',
          borderRadius: '0.5rem',
          padding: '0.65rem 1rem',
          fontSize: '0.825rem',
          fontWeight: 500,
          marginBottom: '1.25rem',
        }}
      >
        <CheckCircle2 size={16} />
        <span>
          Schema & Integrity Validated: <strong>{validation.filename}</strong> strictly conforms to required schema{' '}
          <code>case_id,deletion_status,steps_json</code> with 0 errors or warnings.
        </span>
      </div>
    );
  }

  if (hasErrors) {
    return (
      <div
        style={{
          backgroundColor: 'var(--phase-finding-bg)',
          border: '1px solid var(--phase-finding-border)',
          color: 'var(--phase-finding)',
          borderRadius: '0.5rem',
          padding: '0.85rem 1.25rem',
          marginBottom: '1.25rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontWeight: 600 }}>
          <AlertCircle size={18} />
          <span>File Ingestion Errors in {validation.filename}</span>
        </div>
        <ul style={{ margin: '0.5rem 0 0 1.6rem', fontSize: '0.825rem', lineHeight: 1.6 }}>
          {validation.errors.map((err, i) => (
            <li key={i}>{err}</li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <div
      style={{
        backgroundColor: 'var(--status-incomplete-bg)',
        border: '1px solid var(--status-incomplete-border)',
        color: 'var(--status-incomplete)',
        borderRadius: '0.5rem',
        padding: '0.75rem 1rem',
        marginBottom: '1.25rem',
        fontSize: '0.825rem',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
        }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600 }}>
          <AlertTriangle size={16} />
          <span>
            {validation.warnings.length} Parsing / Integrity Notice
            {validation.warnings.length === 1 ? '' : 's'} in {validation.filename}
          </span>
        </div>
        <button
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem',
            color: 'inherit',
            fontSize: '0.75rem',
            fontWeight: 600,
          }}
        >
          {isExpanded ? (
            <>
              Hide details <ChevronUp size={14} />
            </>
          ) : (
            <>
              Show details ({validation.warnings.length}) <ChevronDown size={14} />
            </>
          )}
        </button>
      </div>

      {isExpanded && (
        <div
          style={{
            marginTop: '0.65rem',
            paddingTop: '0.65rem',
            borderTop: '1px solid var(--status-incomplete-border)',
            maxHeight: '200px',
            overflowY: 'auto',
          }}
        >
          <ul style={{ margin: '0 0 0 1.25rem', lineHeight: 1.6 }}>
            {validation.warnings.map((warn, i) => (
              <li key={i}>{warn}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
