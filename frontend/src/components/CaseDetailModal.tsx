import React, { useState } from 'react';
import type { AuditCase, AuditStep } from '../types';
import {
  X,
  Shield,
  HelpCircle,
  Copy,
  Check,
  Server,
  Code2,
  ListOrdered,
  AlertTriangle,
  Info,
} from 'lucide-react';

interface CaseDetailModalProps {
  auditCase: AuditCase | null;
  onClose: () => void;
}

export const CaseDetailModal: React.FC<CaseDetailModalProps> = ({ auditCase, onClose }) => {
  const [activeTab, setActiveTab] = useState<'ALL' | 'FINDING' | 'REMEDIATION' | 'VERIFICATION' | 'RAW_JSON'>('ALL');
  const [copied, setCopied] = useState(false);

  if (!auditCase) return null;

  const handleCopyJSON = () => {
    try {
      const formatted = JSON.stringify(JSON.parse(auditCase.raw_steps_json), null, 2);
      navigator.clipboard.writeText(formatted);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      navigator.clipboard.writeText(auditCase.raw_steps_json);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const stepsToDisplay =
    activeTab === 'ALL' || activeTab === 'RAW_JSON'
      ? auditCase.steps
      : auditCase.steps.filter((s) => s.phase === activeTab);

  let statusBadgeClass = 'badge-na';
  if (auditCase.deletion_status === 'COMPLETE') statusBadgeClass = 'badge-complete';
  if (auditCase.deletion_status === 'INCOMPLETE') statusBadgeClass = 'badge-incomplete';

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.65)',
        backdropFilter: 'blur(3px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1.25rem',
        zIndex: 50,
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: 'var(--bg-card)',
          borderRadius: '0.85rem',
          border: '1px solid var(--border)',
          width: '100%',
          maxWidth: '850px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: 'var(--shadow-lg)',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '1rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)' }}>
              Case <code>{auditCase.case_id}</code>
            </h2>
            <span className={`badge ${statusBadgeClass}`}>
              {auditCase.deletion_status}
            </span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              ({auditCase.steps.length} total steps)
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <button
              onClick={handleCopyJSON}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                backgroundColor: 'var(--bg-subtle)',
                color: 'var(--text-main)',
                border: '1px solid var(--border)',
                borderRadius: '0.4rem',
                padding: '0.35rem 0.65rem',
                fontSize: '0.75rem',
                fontWeight: 600,
              }}
            >
              {copied ? <Check size={14} color="var(--status-complete)" /> : <Copy size={14} />}
              <span>{copied ? 'Copied' : 'Copy JSON'}</span>
            </button>
            <button
              onClick={onClose}
              style={{
                color: 'var(--text-muted)',
                padding: '0.35rem',
                borderRadius: '0.4rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
              title="Close modal"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Phase Filter Tabs */}
        <div
          style={{
            display: 'flex',
            gap: '0.5rem',
            padding: '0.75rem 1.5rem',
            borderBottom: '1px solid var(--border)',
            backgroundColor: 'var(--bg-subtle)',
            overflowX: 'auto',
          }}
        >
          <button
            onClick={() => setActiveTab('ALL')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              padding: '0.35rem 0.75rem',
              fontSize: '0.8rem',
              fontWeight: 600,
              borderRadius: '0.4rem',
              color: activeTab === 'ALL' ? '#ffffff' : 'var(--text-muted)',
              backgroundColor: activeTab === 'ALL' ? 'var(--primary)' : 'transparent',
            }}
          >
            <ListOrdered size={14} />
            All Steps ({auditCase.steps.length})
          </button>

          {auditCase.findings_count > 0 && (
            <button
              onClick={() => setActiveTab('FINDING')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.35rem 0.75rem',
                fontSize: '0.8rem',
                fontWeight: 600,
                borderRadius: '0.4rem',
                color: activeTab === 'FINDING' ? '#ffffff' : 'var(--phase-finding)',
                backgroundColor: activeTab === 'FINDING' ? 'var(--phase-finding)' : 'transparent',
              }}
            >
              Findings ({auditCase.findings_count})
            </button>
          )}

          {auditCase.remediations_count > 0 && (
            <button
              onClick={() => setActiveTab('REMEDIATION')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.35rem 0.75rem',
                fontSize: '0.8rem',
                fontWeight: 600,
                borderRadius: '0.4rem',
                color: activeTab === 'REMEDIATION' ? '#ffffff' : 'var(--phase-remediation)',
                backgroundColor: activeTab === 'REMEDIATION' ? 'var(--phase-remediation)' : 'transparent',
              }}
            >
              Remediations ({auditCase.remediations_count})
            </button>
          )}

          {auditCase.verifications_count > 0 && (
            <button
              onClick={() => setActiveTab('VERIFICATION')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.35rem 0.75rem',
                fontSize: '0.8rem',
                fontWeight: 600,
                borderRadius: '0.4rem',
                color: activeTab === 'VERIFICATION' ? '#ffffff' : 'var(--phase-verification)',
                backgroundColor: activeTab === 'VERIFICATION' ? 'var(--phase-verification)' : 'transparent',
              }}
            >
              Verifications ({auditCase.verifications_count})
            </button>
          )}

          <button
            onClick={() => setActiveTab('RAW_JSON')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              padding: '0.35rem 0.75rem',
              fontSize: '0.8rem',
              fontWeight: 600,
              borderRadius: '0.4rem',
              color: activeTab === 'RAW_JSON' ? '#ffffff' : 'var(--text-muted)',
              backgroundColor: activeTab === 'RAW_JSON' ? 'var(--text-main)' : 'transparent',
              marginLeft: 'auto',
            }}
          >
            <Code2 size={14} />
            Raw JSON
          </button>
        </div>

        {/* Content Body */}
        <div style={{ padding: '1.25rem 1.5rem', overflowY: 'auto', flex: 1 }}>
          {/* Remediation Policy Notice Callout */}
          {auditCase.deletion_status === 'INCOMPLETE' && (
            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '0.65rem',
                backgroundColor: 'var(--phase-remediation-bg)',
                border: '1px solid var(--phase-remediation-border)',
                color: 'var(--phase-remediation)',
                borderRadius: '0.5rem',
                padding: '0.75rem 1rem',
                fontSize: '0.8rem',
                lineHeight: 1.5,
                marginBottom: '1rem',
              }}
            >
              <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: '0.1rem' }} />
              <div>
                <strong>Notice: Planned Remediation Actions. </strong>
                Remediation steps specify required policy actions to achieve compliance. They are planned actions, not proof of completed work. In accordance with the challenge specification, proposed remediations and post-remediation verification checks deliberately cite an empty evidence ID (<code>""</code>).
              </div>
            </div>
          )}

          {auditCase.deletion_status === 'NOT_APPLICABLE' && (
            <div
              style={{
                textAlign: 'center',
                padding: '3rem 1.5rem',
                backgroundColor: 'var(--bg-subtle)',
                borderRadius: '0.5rem',
                color: 'var(--text-muted)',
              }}
            >
              <Info size={36} color="var(--status-na)" style={{ margin: '0 auto 0.75rem' }} />
              <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-main)' }}>
                Non-Deletion Request (Empty Steps Array)
              </h3>
              <p style={{ fontSize: '0.85rem', maxWidth: '480px', margin: '0.5rem auto 0' }}>
                This request was classified as <code>NOT_APPLICABLE</code> (such as a general inquiry, data access question, or marketing preference update). Because no deletion was authorized, <code>steps_json</code> is empty (<code>[]</code>).
              </p>
            </div>
          )}

          {activeTab === 'RAW_JSON' ? (
            <pre
              style={{
                backgroundColor: 'var(--bg-app)',
                border: '1px solid var(--border)',
                borderRadius: '0.5rem',
                padding: '1rem',
                fontSize: '0.8rem',
                color: 'var(--text-main)',
                overflowX: 'auto',
                fontFamily: 'Consolas, Monaco, monospace',
                lineHeight: 1.5,
              }}
            >
              {JSON.stringify(JSON.parse(auditCase.raw_steps_json || '[]'), null, 2)}
            </pre>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {stepsToDisplay.map((step) => (
                <StepCard key={step.step_no} step={step} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const StepCard: React.FC<{ step: AuditStep }> = ({ step }) => {
  let phaseBadgeClass = 'badge-verification';
  if (step.phase === 'FINDING') phaseBadgeClass = 'badge-finding';
  if (step.phase === 'REMEDIATION') phaseBadgeClass = 'badge-remediation';

  const hasEvidenceCitation = step.evidence_id && step.evidence_id.trim() !== '';

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: '0.65rem',
        padding: '0.9rem 1.15rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.6rem',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      {/* Top row: Step No, Phase, Operation */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <span
            style={{
              backgroundColor: 'var(--bg-subtle)',
              border: '1px solid var(--border)',
              borderRadius: '0.35rem',
              padding: '0.15rem 0.45rem',
              fontSize: '0.75rem',
              fontWeight: 700,
              color: 'var(--text-main)',
            }}
          >
            Step #{step.step_no}
          </span>
          <span className={`badge ${phaseBadgeClass}`}>{step.phase}</span>
          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)' }}>
            <code>{step.operation}</code>
          </span>
        </div>

        {/* State Tag */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Target State:</span>
          <span
            style={{
              fontSize: '0.75rem',
              fontWeight: 700,
              padding: '0.15rem 0.5rem',
              borderRadius: '0.3rem',
              backgroundColor:
                step.state === 'PRESENT'
                  ? 'var(--phase-finding-bg)'
                  : step.state === 'ABSENT' || step.state === 'DISABLED' || step.state === 'BLOCKED'
                  ? 'var(--phase-verification-bg)'
                  : 'var(--bg-subtle)',
              color:
                step.state === 'PRESENT'
                  ? 'var(--phase-finding)'
                  : step.state === 'ABSENT' || step.state === 'DISABLED' || step.state === 'BLOCKED'
                  ? 'var(--phase-verification)'
                  : 'var(--text-main)',
              border: '1px solid var(--border)',
            }}
          >
            {step.state}
          </span>
        </div>
      </div>

      {/* Middle row: System & Resource */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '1.25rem',
          fontSize: '0.8rem',
          color: 'var(--text-muted)',
          backgroundColor: 'var(--bg-app)',
          padding: '0.45rem 0.75rem',
          borderRadius: '0.4rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <Server size={14} color="var(--primary)" />
          <span>System:</span>
          <strong style={{ color: 'var(--text-main)' }}>{step.system_id}</strong>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span>Resource:</span>
          <code style={{ color: 'var(--text-main)' }}>{step.resource_id}</code>
        </div>
      </div>

      {/* Bottom row: Evidence Citation vs Proposed Action */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.775rem' }}>
        {hasEvidenceCitation ? (
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.35rem',
              color: 'var(--status-complete)',
              backgroundColor: 'var(--status-complete-bg)',
              border: '1px solid var(--status-complete-border)',
              padding: '0.2rem 0.55rem',
              borderRadius: '0.35rem',
              fontWeight: 500,
            }}
          >
            <Shield size={13} />
            <span>
              Verified Evidence Citation: <strong>{step.evidence_id}</strong>
            </span>
          </div>
        ) : (
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.35rem',
              color: 'var(--status-incomplete)',
              backgroundColor: 'var(--status-incomplete-bg)',
              border: '1px solid var(--status-incomplete-border)',
              padding: '0.2rem 0.55rem',
              borderRadius: '0.35rem',
              fontWeight: 500,
            }}
            title="Future remediation or post-remediation verification steps cite an empty evidence_id per problem specification."
          >
            <HelpCircle size={13} />
            <span>Proposed Action — Empty Citation (Unverified at Audit Time)</span>
          </div>
        )}
      </div>
    </div>
  );
};
