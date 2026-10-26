import React, { useState, useEffect, useCallback } from 'react';
import './styles/theme.css';
import type { AuditCase, OverviewStats, ValidationResult } from './types';
import { parseOutputCSV } from './utils/csvParser';
import { calculateStats } from './utils/stats';
import { Header } from './components/Header';
import { Overview } from './components/Overview';
import { ValidationBanner } from './components/ValidationBanner';
import { CaseExplorer } from './components/CaseExplorer';
import { CaseDetailModal } from './components/CaseDetailModal';
import { ShieldCheck, Loader2 } from 'lucide-react';

export const App: React.FC = () => {
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    const saved = localStorage.getItem('ghost_data_theme');
    if (saved === 'dark' || saved === 'light') return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  const [cases, setCases] = useState<AuditCase[]>([]);
  const [validation, setValidation] = useState<ValidationResult>({
    cases: [],
    warnings: [],
    errors: [],
    total_rows: 0,
    is_valid_header: true,
    filename: 'output.csv',
  });
  const [stats, setStats] = useState<OverviewStats>(() => calculateStats([]));
  const [selectedCase, setSelectedCase] = useState<AuditCase | null>(null);
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'COMPLETE' | 'INCOMPLETE' | 'NOT_APPLICABLE'>('ALL');
  const [loading, setLoading] = useState(true);
  const [isDragOver, setIsDragOver] = useState(false);

  // Apply theme to document element
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('ghost_data_theme', theme);
  }, [theme]);

  // Load default dataset on mount
  const loadDefaultDataset = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch('/default_output.csv');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: Failed to fetch default output.csv`);
      }
      const text = await response.text();
      const result = parseOutputCSV(text, 'output.csv (Repository Default)');
      setValidation(result);
      setCases(result.cases);
      setStats(calculateStats(result.cases));
    } catch (err) {
      console.warn('Could not load /default_output.csv:', err);
      // Fallback demo row so dashboard is never empty even without fetch
      const demoCSV = `case_id,deletion_status,steps_json
case_33,INCOMPLETE,"[{\\"step_no\\":1,\\"phase\\":\\"FINDING\\",\\"system_id\\":\\"account_service\\",\\"resource_id\\":\\"account_history_report\\",\\"operation\\":\\"REPORT_REMAINING_RECORD\\",\\"state\\":\\"PRESENT\\",\\"evidence_id\\":\\"evidence_18\\"},{\\"step_no\\":2,\\"phase\\":\\"REMEDIATION\\",\\"system_id\\":\\"account_service\\",\\"resource_id\\":\\"account_history_report\\",\\"operation\\":\\"DELETE_RECORD\\",\\"state\\":\\"ABSENT\\",\\"evidence_id\\":\\"\\"},{\\"step_no\\":3,\\"phase\\":\\"VERIFICATION\\",\\"system_id\\":\\"account_service\\",\\"resource_id\\":\\"account_history_report\\",\\"operation\\":\\"VERIFY_RECORD_ABSENT\\",\\"state\\":\\"ABSENT\\",\\"evidence_id\\":\\"\\"}]"
case_34,COMPLETE,"[{\\"step_no\\":1,\\"phase\\":\\"VERIFICATION\\",\\"system_id\\":\\"account_service\\",\\"resource_id\\":\\"account_5762\\",\\"operation\\":\\"VERIFY_RECORD_ABSENT\\",\\"state\\":\\"ABSENT\\",\\"evidence_id\\":\\"evidence_01\\"}]"
case_35,NOT_APPLICABLE,[]`;
      const result = parseOutputCSV(demoCSV, 'demo_fallback.csv');
      setValidation(result);
      setCases(result.cases);
      setStats(calculateStats(result.cases));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDefaultDataset();
  }, [loadDefaultDataset]);

  // Handle custom CSV file upload
  const handleFileUpload = (file: File) => {
    setLoading(true);
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const result = parseOutputCSV(text, file.name);
      setValidation(result);
      setCases(result.cases);
      setStats(calculateStats(result.cases));
      setStatusFilter('ALL');
      setLoading(false);
    };
    reader.onerror = () => {
      alert('Failed to read the selected file.');
      setLoading(false);
    };
    reader.readAsText(file, 'UTF-8');
  };

  const handleToggleTheme = () => {
    setTheme((t) => (t === 'dark' ? 'light' : 'dark'));
  };

  // Drag and Drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file && (file.name.endsWith('.csv') || file.type === 'text/csv')) {
      handleFileUpload(file);
    } else {
      alert('Please drop a valid .csv file.');
    }
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
      }}
    >
      {/* Drag overlay indicator */}
      {isDragOver && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(37, 99, 235, 0.85)',
            zIndex: 100,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#ffffff',
            pointerEvents: 'none',
          }}
        >
          <ShieldCheck size={64} />
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '1rem' }}>
            Drop output.csv to inspect audit cases
          </h2>
          <p style={{ fontSize: '0.9rem', marginTop: '0.35rem', opacity: 0.9 }}>
            Files are parsed 100% locally in your browser
          </p>
        </div>
      )}

      {/* Header */}
      <Header
        theme={theme}
        onToggleTheme={handleToggleTheme}
        onFileUpload={handleFileUpload}
        onResetDefault={loadDefaultDataset}
        currentFilename={validation.filename}
        totalCases={cases.length}
      />

      {/* Main Content */}
      <main className="container" style={{ flex: 1 }}>
        {loading ? (
          <div
            style={{
              padding: '6rem 0',
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '1rem',
              color: 'var(--text-muted)',
            }}
          >
            <Loader2 size={36} color="var(--primary)" style={{ animation: 'spin 1s linear infinite' }} />
            <p style={{ fontSize: '0.9rem' }}>Loading and parsing audit predictions...</p>
          </div>
        ) : (
          <>
            {/* Validation Banner */}
            <ValidationBanner validation={validation} />

            {/* Overview KPIs and Distribution */}
            <Overview
              stats={stats}
              onFilterStatus={(st) => setStatusFilter(st)}
              activeFilter={statusFilter}
            />

            {/* Case Explorer and Table */}
            <CaseExplorer
              cases={cases}
              onSelectCase={(c) => setSelectedCase(c)}
              statusFilter={statusFilter}
              onStatusFilterChange={setStatusFilter}
            />
          </>
        )}
      </main>

      {/* Case Detail Modal */}
      <CaseDetailModal auditCase={selectedCase} onClose={() => setSelectedCase(null)} />

      {/* Footer */}
      <footer
        style={{
          borderTop: '1px solid var(--border)',
          backgroundColor: 'var(--bg-card)',
          padding: '1.25rem 0',
          marginTop: '3rem',
          fontSize: '0.8rem',
          color: 'var(--text-muted)',
        }}
      >
        <div
          className="container"
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '1rem',
            paddingTop: 0,
            paddingBottom: 0,
          }}
        >
          <div>
            <span>HackerRank Orchestrate October 2026 — </span>
            <strong style={{ color: 'var(--text-main)' }}>Ghost Data Still Exists</strong>
          </div>
          <div>
            <span>Contract Reference: </span>
            <a
              href="https://wwww.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists"
              target="_blank"
              rel="noreferrer"
              style={{ color: 'var(--primary)', textDecoration: 'none', fontWeight: 600 }}
            >
              Challenge Portal
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
