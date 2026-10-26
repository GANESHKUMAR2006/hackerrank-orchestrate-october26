import React, { useRef } from 'react';
import { ShieldCheck, Upload, RotateCcw, Sun, Moon, FileText } from 'lucide-react';

interface HeaderProps {
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
  onFileUpload: (file: File) => void;
  onResetDefault: () => void;
  currentFilename: string;
  totalCases: number;
}

export const Header: React.FC<HeaderProps> = ({
  theme,
  onToggleTheme,
  onFileUpload,
  onResetDefault,
  currentFilename,
  totalCases,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onFileUpload(file);
      // Reset input so same file can be re-uploaded if modified
      e.target.value = '';
    }
  };

  return (
    <header
      style={{
        backgroundColor: 'var(--bg-card)',
        borderBottom: '1px solid var(--border)',
        padding: '1rem 0',
        boxShadow: 'var(--shadow-sm)',
        position: 'sticky',
        top: 0,
        zIndex: 40,
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
        {/* Brand / Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div
            style={{
              backgroundColor: 'var(--primary-light)',
              color: 'var(--primary)',
              borderRadius: '0.6rem',
              padding: '0.6rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <ShieldCheck size={28} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <h1
                style={{
                  fontSize: '1.25rem',
                  fontWeight: 700,
                  color: 'var(--text-main)',
                  letterSpacing: '-0.02em',
                }}
              >
                Ghost Data Still Exists
              </h1>
              <span
                style={{
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  backgroundColor: 'var(--bg-subtle)',
                  color: 'var(--text-muted)',
                  border: '1px solid var(--border)',
                  borderRadius: '0.25rem',
                  padding: '0.1rem 0.4rem',
                }}
              >
                Audit Dashboard
              </span>
            </div>
            <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)' }}>
              AI Deletion Audit & State Reconstruction Verification Engine
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
          {/* Active file indicator */}
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              backgroundColor: 'var(--bg-subtle)',
              border: '1px solid var(--border)',
              borderRadius: '0.5rem',
              padding: '0.4rem 0.75rem',
              fontSize: '0.8rem',
              color: 'var(--text-muted)',
            }}
            title={`Active dataset: ${currentFilename} (${totalCases} cases)`}
          >
            <FileText size={15} color="var(--primary)" />
            <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>{currentFilename}</span>
            <span>({totalCases} cases)</span>
          </div>

          {/* Hidden File Input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />

          {/* Upload Button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              backgroundColor: 'var(--primary)',
              color: '#ffffff',
              borderRadius: '0.5rem',
              padding: '0.45rem 0.85rem',
              fontSize: '0.825rem',
              fontWeight: 600,
              transition: 'background-color 0.15s ease',
            }}
            onMouseOver={(e) => (e.currentTarget.style.backgroundColor = 'var(--primary-hover)')}
            onMouseOut={(e) => (e.currentTarget.style.backgroundColor = 'var(--primary)')}
          >
            <Upload size={15} />
            <span>Upload CSV</span>
          </button>

          {/* Reset to Default Button */}
          <button
            onClick={onResetDefault}
            title="Reload repository output.csv"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.35rem',
              backgroundColor: 'var(--bg-card)',
              color: 'var(--text-muted)',
              border: '1px solid var(--border)',
              borderRadius: '0.5rem',
              padding: '0.45rem 0.75rem',
              fontSize: '0.825rem',
              fontWeight: 500,
              transition: 'background-color 0.15s ease',
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)';
              e.currentTarget.style.color = 'var(--text-main)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--bg-card)';
              e.currentTarget.style.color = 'var(--text-muted)';
            }}
          >
            <RotateCcw size={14} />
            <span>Reset</span>
          </button>

          {/* Theme Switcher */}
          <button
            onClick={onToggleTheme}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '36px',
              height: '36px',
              backgroundColor: 'var(--bg-card)',
              color: 'var(--text-main)',
              border: '1px solid var(--border)',
              borderRadius: '0.5rem',
              transition: 'background-color 0.15s ease',
            }}
            onMouseOver={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)')}
            onMouseOut={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-card)')}
          >
            {theme === 'dark' ? <Sun size={17} color="#fbbf24" /> : <Moon size={17} color="#6366f1" />}
          </button>
        </div>
      </div>
    </header>
  );
};
