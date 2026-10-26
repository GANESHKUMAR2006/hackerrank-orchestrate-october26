import React, { useState, useMemo } from 'react';
import type { AuditCase } from '../types';
import {
  Search,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  ArrowUpDown,
  SlidersHorizontal,
  FolderOpen,
} from 'lucide-react';

interface CaseExplorerProps {
  cases: AuditCase[];
  onSelectCase: (c: AuditCase) => void;
  statusFilter: string;
  onStatusFilterChange: (status: 'ALL' | 'COMPLETE' | 'INCOMPLETE' | 'NOT_APPLICABLE') => void;
}

type SortField = 'case_id' | 'status' | 'steps';
type SortOrder = 'asc' | 'desc';

export const CaseExplorer: React.FC<CaseExplorerProps> = ({
  cases,
  onSelectCase,
  statusFilter,
  onStatusFilterChange,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [phaseFilter, setPhaseFilter] = useState<'ALL' | 'FINDINGS' | 'REMEDIATIONS' | 'VERIFICATIONS'>('ALL');
  const [sortField, setSortField] = useState<SortField>('case_id');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  // Filter & Sort
  const filteredCases = useMemo(() => {
    let result = cases;

    // Search filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter((c) => c.case_id.toLowerCase().includes(q));
    }

    // Status filter
    if (statusFilter !== 'ALL') {
      result = result.filter((c) => c.deletion_status === statusFilter);
    }

    // Phase filter
    if (phaseFilter === 'FINDINGS') {
      result = result.filter((c) => c.findings_count > 0);
    } else if (phaseFilter === 'REMEDIATIONS') {
      result = result.filter((c) => c.remediations_count > 0);
    } else if (phaseFilter === 'VERIFICATIONS') {
      result = result.filter((c) => c.verifications_count > 0);
    }

    // Sort
    result = [...result].sort((a, b) => {
      let comp = 0;
      if (sortField === 'case_id') {
        const numA = parseInt(a.case_id.replace(/\D/g, ''), 10) || 0;
        const numB = parseInt(b.case_id.replace(/\D/g, ''), 10) || 0;
        comp = numA - numB;
      } else if (sortField === 'status') {
        comp = a.deletion_status.localeCompare(b.deletion_status);
      } else if (sortField === 'steps') {
        comp = a.steps.length - b.steps.length;
      }

      return sortOrder === 'asc' ? comp : -comp;
    });

    return result;
  }, [cases, searchQuery, statusFilter, phaseFilter, sortField, sortOrder]);

  // Pagination calculation
  const totalPages = Math.max(1, Math.ceil(filteredCases.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const startIndex = (currentPage - 1) * pageSize;
  const paginatedCases = filteredCases.slice(startIndex, startIndex + pageSize);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
    setPage(1);
  };

  return (
    <section
      style={{
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: '0.75rem',
        boxShadow: 'var(--shadow-sm)',
        overflow: 'hidden',
      }}
    >
      {/* Controls Bar */}
      <div
        style={{
          padding: '1.25rem',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
        }}
      >
        {/* Left: Search input */}
        <div style={{ position: 'relative', minWidth: '240px', flex: '1 1 240px' }}>
          <Search
            size={16}
            color="var(--text-subtle)"
            style={{ position: 'absolute', left: '0.85rem', top: '50%', transform: 'translateY(-50%)' }}
          />
          <input
            type="text"
            placeholder="Search by case ID (e.g. case_33)..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(1);
            }}
            style={{
              width: '100%',
              padding: '0.55rem 0.85rem 0.55rem 2.35rem',
              borderRadius: '0.5rem',
              border: '1px solid var(--border)',
              backgroundColor: 'var(--bg-app)',
              color: 'var(--text-main)',
              fontSize: '0.85rem',
              outline: 'none',
              transition: 'border-color 0.15s ease',
            }}
            onFocus={(e) => (e.target.style.borderColor = 'var(--border-focus)')}
            onBlur={(e) => (e.target.style.borderColor = 'var(--border)')}
          />
        </div>

        {/* Right: Filters and Selectors */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
          {/* Status Filter Buttons */}
          <div
            style={{
              display: 'inline-flex',
              backgroundColor: 'var(--bg-subtle)',
              padding: '0.2rem',
              borderRadius: '0.5rem',
              border: '1px solid var(--border)',
            }}
          >
            {(['ALL', 'COMPLETE', 'INCOMPLETE', 'NOT_APPLICABLE'] as const).map((st) => (
              <button
                key={st}
                onClick={() => {
                  onStatusFilterChange(st);
                  setPage(1);
                }}
                style={{
                  padding: '0.35rem 0.65rem',
                  fontSize: '0.75rem',
                  fontWeight: statusFilter === st ? 600 : 500,
                  borderRadius: '0.35rem',
                  color: statusFilter === st ? '#ffffff' : 'var(--text-muted)',
                  backgroundColor:
                    statusFilter === st
                      ? st === 'COMPLETE'
                        ? 'var(--status-complete)'
                        : st === 'INCOMPLETE'
                        ? 'var(--status-incomplete)'
                        : st === 'NOT_APPLICABLE'
                        ? 'var(--status-na)'
                        : 'var(--primary)'
                      : 'transparent',
                  transition: 'all 0.15s ease',
                }}
              >
                {st === 'ALL'
                  ? 'All Statuses'
                  : st === 'NOT_APPLICABLE'
                  ? 'N/A'
                  : st.charAt(0) + st.slice(1).toLowerCase()}
              </button>
            ))}
          </div>

          {/* Phase Filter Dropdown */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            <SlidersHorizontal size={14} color="var(--text-subtle)" />
            <select
              value={phaseFilter}
              onChange={(e) => {
                setPhaseFilter(e.target.value as any);
                setPage(1);
              }}
              style={{
                padding: '0.45rem 0.65rem',
                borderRadius: '0.5rem',
                border: '1px solid var(--border)',
                backgroundColor: 'var(--bg-card)',
                color: 'var(--text-main)',
                fontSize: '0.8rem',
                cursor: 'pointer',
              }}
            >
              <option value="ALL">All Phases</option>
              <option value="FINDINGS">With Findings</option>
              <option value="REMEDIATIONS">With Remediations</option>
              <option value="VERIFICATIONS">With Verifications</option>
            </select>
          </div>
        </div>
      </div>

      {/* Table / List Container */}
      <div style={{ overflowX: 'auto' }}>
        {filteredCases.length === 0 ? (
          <div
            style={{
              padding: '4rem 1.5rem',
              textAlign: 'center',
              color: 'var(--text-muted)',
            }}
          >
            <FolderOpen size={40} color="var(--text-subtle)" style={{ margin: '0 auto 0.75rem' }} />
            <div style={{ fontWeight: 600, fontSize: '1rem', color: 'var(--text-main)' }}>
              No audit cases match your search
            </div>
            <p style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>
              Try adjusting your search query, status filters, or phase restrictions.
            </p>
          </div>
        ) : (
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              textAlign: 'left',
              fontSize: '0.85rem',
            }}
          >
            <thead>
              <tr
                style={{
                  backgroundColor: 'var(--bg-subtle)',
                  borderBottom: '1px solid var(--border)',
                  color: 'var(--text-muted)',
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                <th
                  onClick={() => handleSort('case_id')}
                  style={{ padding: '0.75rem 1.25rem', cursor: 'pointer', userSelect: 'none' }}
                >
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                    Case ID <ArrowUpDown size={12} />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('status')}
                  style={{ padding: '0.75rem 1.25rem', cursor: 'pointer', userSelect: 'none' }}
                >
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                    Audit Status <ArrowUpDown size={12} />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('steps')}
                  style={{ padding: '0.75rem 1.25rem', cursor: 'pointer', userSelect: 'none' }}
                >
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                    Total Steps <ArrowUpDown size={12} />
                  </div>
                </th>
                <th style={{ padding: '0.75rem 1.25rem' }}>Phase Composition</th>
                <th style={{ padding: '0.75rem 1.25rem', textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {paginatedCases.map((c) => {
                let badgeClass = 'badge-na';
                if (c.deletion_status === 'COMPLETE') badgeClass = 'badge-complete';
                if (c.deletion_status === 'INCOMPLETE') badgeClass = 'badge-incomplete';

                return (
                  <tr
                    key={c.case_id}
                    onClick={() => onSelectCase(c)}
                    style={{
                      borderBottom: '1px solid var(--border)',
                      cursor: 'pointer',
                      transition: 'background-color 0.15s ease',
                    }}
                    onMouseOver={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)')}
                    onMouseOut={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    {/* Case ID */}
                    <td style={{ padding: '0.85rem 1.25rem', fontWeight: 600, color: 'var(--text-main)' }}>
                      <code>{c.case_id}</code>
                    </td>

                    {/* Status Badge */}
                    <td style={{ padding: '0.85rem 1.25rem' }}>
                      <span className={`badge ${badgeClass}`}>
                        {c.deletion_status}
                      </span>
                    </td>

                    {/* Steps count */}
                    <td style={{ padding: '0.85rem 1.25rem', color: 'var(--text-muted)' }}>
                      <strong>{c.steps.length}</strong> step{c.steps.length === 1 ? '' : 's'}
                    </td>

                    {/* Phase composition chips */}
                    <td style={{ padding: '0.85rem 1.25rem' }}>
                      <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                        {c.findings_count > 0 && (
                          <span
                            className="badge badge-finding"
                            style={{ fontSize: '0.7rem', padding: '0.1rem 0.45rem' }}
                          >
                            {c.findings_count} Finding{c.findings_count === 1 ? '' : 's'}
                          </span>
                        )}
                        {c.remediations_count > 0 && (
                          <span
                            className="badge badge-remediation"
                            style={{ fontSize: '0.7rem', padding: '0.1rem 0.45rem' }}
                          >
                            {c.remediations_count} Remediation{c.remediations_count === 1 ? '' : 's'}
                          </span>
                        )}
                        {c.verifications_count > 0 && (
                          <span
                            className="badge badge-verification"
                            style={{ fontSize: '0.7rem', padding: '0.1rem 0.45rem' }}
                          >
                            {c.verifications_count} Verification{c.verifications_count === 1 ? '' : 's'}
                          </span>
                        )}
                        {c.steps.length === 0 && (
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-subtle)' }}>None (empty array)</span>
                        )}
                      </div>
                    </td>

                    {/* Action */}
                    <td style={{ padding: '0.85rem 1.25rem', textAlign: 'right' }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectCase(c);
                        }}
                        style={{
                          fontSize: '0.775rem',
                          fontWeight: 600,
                          color: 'var(--primary)',
                          padding: '0.25rem 0.55rem',
                          borderRadius: '0.35rem',
                          backgroundColor: 'var(--primary-light)',
                        }}
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination Bar */}
      {filteredCases.length > 0 && (
        <div
          style={{
            padding: '0.85rem 1.25rem',
            borderTop: '1px solid var(--border)',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '1rem',
            fontSize: '0.8rem',
            color: 'var(--text-muted)',
          }}
        >
          <div>
            Showing <strong>{startIndex + 1}</strong> to{' '}
            <strong>{Math.min(startIndex + pageSize, filteredCases.length)}</strong> of{' '}
            <strong>{filteredCases.length}</strong> cases
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ marginRight: '0.25rem' }}>Rows per page:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setPage(1);
              }}
              style={{
                padding: '0.2rem 0.4rem',
                borderRadius: '0.35rem',
                border: '1px solid var(--border)',
                backgroundColor: 'var(--bg-card)',
                color: 'var(--text-main)',
                fontSize: '0.8rem',
              }}
            >
              {[10, 25, 50, 100].map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', marginLeft: '0.5rem' }}>
              <button
                disabled={currentPage === 1}
                onClick={() => setPage(1)}
                style={{
                  padding: '0.35rem',
                  borderRadius: '0.35rem',
                  border: '1px solid var(--border)',
                  color: currentPage === 1 ? 'var(--text-subtle)' : 'var(--text-main)',
                  cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                }}
                title="First Page"
              >
                <ChevronsLeft size={15} />
              </button>
              <button
                disabled={currentPage === 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                style={{
                  padding: '0.35rem',
                  borderRadius: '0.35rem',
                  border: '1px solid var(--border)',
                  color: currentPage === 1 ? 'var(--text-subtle)' : 'var(--text-main)',
                  cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                }}
                title="Previous Page"
              >
                <ChevronLeft size={15} />
              </button>

              <span style={{ padding: '0 0.5rem' }}>
                Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong>
              </span>

              <button
                disabled={currentPage === totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                style={{
                  padding: '0.35rem',
                  borderRadius: '0.35rem',
                  border: '1px solid var(--border)',
                  color: currentPage === totalPages ? 'var(--text-subtle)' : 'var(--text-main)',
                  cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
                }}
                title="Next Page"
              >
                <ChevronRight size={15} />
              </button>
              <button
                disabled={currentPage === totalPages}
                onClick={() => setPage(totalPages)}
                style={{
                  padding: '0.35rem',
                  borderRadius: '0.35rem',
                  border: '1px solid var(--border)',
                  color: currentPage === totalPages ? 'var(--text-subtle)' : 'var(--text-main)',
                  cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
                }}
                title="Last Page"
              >
                <ChevronsRight size={15} />
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
