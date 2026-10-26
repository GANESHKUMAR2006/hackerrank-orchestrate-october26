import React from 'react';
import type { OverviewStats } from '../types';
import {
  CheckCircle,
  AlertTriangle,
  FileQuestion,
  Layers,
  Activity,
  AlertOctagon,
  Wrench,
  ShieldAlert,
} from 'lucide-react';

interface OverviewProps {
  stats: OverviewStats;
  onFilterStatus?: (status: 'ALL' | 'COMPLETE' | 'INCOMPLETE' | 'NOT_APPLICABLE') => void;
  activeFilter?: string;
}

export const Overview: React.FC<OverviewProps> = ({ stats, onFilterStatus, activeFilter = 'ALL' }) => {
  return (
    <section style={{ marginBottom: '2rem' }}>
      {/* Disclaimer / Horizon Callout */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '0.75rem',
          backgroundColor: 'var(--bg-subtle)',
          border: '1px solid var(--border)',
          borderRadius: '0.65rem',
          padding: '0.85rem 1.15rem',
          marginBottom: '1.25rem',
          fontSize: '0.825rem',
          lineHeight: 1.5,
          color: 'var(--text-muted)',
        }}
      >
        <ShieldAlert size={20} color="var(--primary)" style={{ flexShrink: 0, marginTop: '0.1rem' }} />
        <div>
          <strong style={{ color: 'var(--text-main)' }}>Point-in-Time Audit Classification Notice: </strong>
          The statuses and actions below represent historical audit findings reconstructed from evidence captured strictly on or before each case's <code>audit_at</code> horizon. A <code>COMPLETE</code> status confirms that required conditions were established by available evidence at audit time; an <code>INCOMPLETE</code> status specifies the required remediation plan, not proof that remediation has subsequently taken place.
        </div>
      </div>

      {/* Main KPI Stat Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '1rem',
          marginBottom: '1.25rem',
        }}
      >
        {/* Total Cases */}
        <div
          onClick={() => onFilterStatus?.('ALL')}
          style={{
            backgroundColor: 'var(--bg-card)',
            border: activeFilter === 'ALL' ? '2px solid var(--primary)' : '1px solid var(--border)',
            borderRadius: '0.75rem',
            padding: '1.25rem',
            boxShadow: 'var(--shadow-sm)',
            cursor: 'pointer',
            transition: 'transform 0.15s ease, box-shadow 0.15s ease',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Total Audited Cases
            </span>
            <Layers size={18} color="var(--text-subtle)" />
          </div>
          <div style={{ fontSize: '1.85rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '0.35rem' }}>
            {stats.total.toLocaleString()}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            {stats.total_steps.toLocaleString()} total audit steps ({stats.avg_steps_per_case.toFixed(1)} avg/case)
          </div>
        </div>

        {/* Complete */}
        <div
          onClick={() => onFilterStatus?.('COMPLETE')}
          style={{
            backgroundColor: 'var(--bg-card)',
            border: activeFilter === 'COMPLETE' ? '2px solid var(--status-complete)' : '1px solid var(--border)',
            borderRadius: '0.75rem',
            padding: '1.25rem',
            boxShadow: 'var(--shadow-sm)',
            cursor: 'pointer',
            transition: 'transform 0.15s ease, box-shadow 0.15s ease',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--status-complete)', textTransform: 'uppercase' }}>
              Complete
            </span>
            <CheckCircle size={18} color="var(--status-complete)" />
          </div>
          <div style={{ fontSize: '1.85rem', fontWeight: 700, color: 'var(--status-complete)', marginTop: '0.35rem' }}>
            {stats.complete.toLocaleString()}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            {stats.complete_pct.toFixed(1)}% of requests — verified deleted or retained
          </div>
        </div>

        {/* Incomplete */}
        <div
          onClick={() => onFilterStatus?.('INCOMPLETE')}
          style={{
            backgroundColor: 'var(--bg-card)',
            border: activeFilter === 'INCOMPLETE' ? '2px solid var(--status-incomplete)' : '1px solid var(--border)',
            borderRadius: '0.75rem',
            padding: '1.25rem',
            boxShadow: 'var(--shadow-sm)',
            cursor: 'pointer',
            transition: 'transform 0.15s ease, box-shadow 0.15s ease',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--status-incomplete)', textTransform: 'uppercase' }}>
              Incomplete
            </span>
            <AlertTriangle size={18} color="var(--status-incomplete)" />
          </div>
          <div style={{ fontSize: '1.85rem', fontWeight: 700, color: 'var(--status-incomplete)', marginTop: '0.35rem' }}>
            {stats.incomplete.toLocaleString()}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            {stats.incomplete_pct.toFixed(1)}% of requests — remediation plan required
          </div>
        </div>

        {/* Not Applicable */}
        <div
          onClick={() => onFilterStatus?.('NOT_APPLICABLE')}
          style={{
            backgroundColor: 'var(--bg-card)',
            border: activeFilter === 'NOT_APPLICABLE' ? '2px solid var(--status-na)' : '1px solid var(--border)',
            borderRadius: '0.75rem',
            padding: '1.25rem',
            boxShadow: 'var(--shadow-sm)',
            cursor: 'pointer',
            transition: 'transform 0.15s ease, box-shadow 0.15s ease',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--status-na)', textTransform: 'uppercase' }}>
              Not Applicable
            </span>
            <FileQuestion size={18} color="var(--status-na)" />
          </div>
          <div style={{ fontSize: '1.85rem', fontWeight: 700, color: 'var(--status-na)', marginTop: '0.35rem' }}>
            {stats.not_applicable.toLocaleString()}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            {stats.not_applicable_pct.toFixed(1)}% — non-deletion inquiries (empty steps)
          </div>
        </div>
      </div>

      {/* Proportional Distribution Visualization Bar */}
      <div
        style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: '0.75rem',
          padding: '1.25rem',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-main)' }}>
            Audit Outcome Distribution
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {stats.total} total cases evaluated
          </span>
        </div>

        {/* Progress Bar Track */}
        <div
          style={{
            display: 'flex',
            height: '14px',
            borderRadius: '9999px',
            overflow: 'hidden',
            backgroundColor: 'var(--bg-subtle)',
            border: '1px solid var(--border)',
          }}
        >
          {stats.complete_pct > 0 && (
            <div
              style={{
                width: `${stats.complete_pct}%`,
                backgroundColor: 'var(--status-complete)',
                transition: 'width 0.4s ease',
              }}
              title={`COMPLETE: ${stats.complete} (${stats.complete_pct.toFixed(1)}%)`}
            />
          )}
          {stats.incomplete_pct > 0 && (
            <div
              style={{
                width: `${stats.incomplete_pct}%`,
                backgroundColor: 'var(--status-incomplete)',
                transition: 'width 0.4s ease',
              }}
              title={`INCOMPLETE: ${stats.incomplete} (${stats.incomplete_pct.toFixed(1)}%)`}
            />
          )}
          {stats.not_applicable_pct > 0 && (
            <div
              style={{
                width: `${stats.not_applicable_pct}%`,
                backgroundColor: 'var(--status-na)',
                transition: 'width 0.4s ease',
              }}
              title={`NOT_APPLICABLE: ${stats.not_applicable} (${stats.not_applicable_pct.toFixed(1)}%)`}
            />
          )}
        </div>

        {/* Sub-Metric Badges: Findings, Remediations, Verifications */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginTop: '1rem',
            paddingTop: '0.85rem',
            borderTop: '1px solid var(--border)',
            gap: '1rem',
            fontSize: '0.8rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <AlertOctagon size={15} color="var(--phase-finding)" />
            <span style={{ color: 'var(--text-muted)' }}>Violation Findings:</span>
            <strong style={{ color: 'var(--phase-finding)' }}>{stats.total_findings.toLocaleString()}</strong>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Wrench size={15} color="var(--phase-remediation)" />
            <span style={{ color: 'var(--text-muted)' }}>Planned Remediations:</span>
            <strong style={{ color: 'var(--phase-remediation)' }}>{stats.total_remediations.toLocaleString()}</strong>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Activity size={15} color="var(--phase-verification)" />
            <span style={{ color: 'var(--text-muted)' }}>Verification Checks:</span>
            <strong style={{ color: 'var(--phase-verification)' }}>{stats.total_verifications.toLocaleString()}</strong>
          </div>
        </div>
      </div>
    </section>
  );
};
