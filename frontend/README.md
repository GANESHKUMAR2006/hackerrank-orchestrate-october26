# Ghost Data Still Exists — Privacy Audit Dashboard

A responsive, client-side React 19 + TypeScript dashboard built for the HackerRank Orchestrate (October 2026) challenge: **"Ghost Data Still Exists"**.

The dashboard ingests and visualizes GDPR/CCPA deletion-audit determinations (`output.csv`), providing compliance auditors and security teams with clear visibility into deletion states, remaining ghost records, and remediation action plans.

---

## Key Features

1. **Compliance Overview**
   - High-level metrics: Total audit cases, `COMPLETE`, `INCOMPLETE`, and `NOT_APPLICABLE` counts.
   - Proportional status distribution bar and phase step count breakdown.
   - **Audit Notice**: Explicit disclaimer that statuses represent point-in-time audit determinations at `audit_at`, not proof of subsequent remediation.

2. **Case Explorer**
   - Instant search across case IDs.
   - Multi-status filter tabs (`ALL`, `INCOMPLETE`, `COMPLETE`, `NOT_APPLICABLE`).
   - Phase filter (`FINDING`, `REMEDIATION`, `VERIFICATION`).
   - Sortable table columns (Case ID, Status, Step Count) with responsive pagination.

3. **Detailed Case Inspection**
   - Sequential audit step inspection preserving exact phase order (`FINDING` → `REMEDIATION` → `VERIFICATION`).
   - Operation details: System ID, Resource ID, Operation name, and Resulting State.
   - **Evidence vs Proposed Action Distinction**:
     - **Verified Evidence**: Highlighted with an evidence pill citing the exact source file ID (e.g. `evidence_18`).
     - **Proposed Remediation / Verification**: Clearly badged as `Empty citation ("") • Proposed action, not evidence`, preventing confusion between historical proof and planned actions.
   - Formatted Raw JSON viewer with one-click copy.

4. **Robust Client-Side CSV Ingestion**
   - Drag-and-drop or file picker for arbitrary audit output CSV files.
   - Custom RFC 4180 parser handling multiline records, escaped quotes (`""`), commas inside JSON arrays, and UTF-8 BOM headers.
   - Pre-loads official baseline `output.csv` (518 cases) out of the box.
   - Comprehensive format validation with collapsible warning drawer for structural defects.

5. **Design & Accessibility**
   - Native dark and light themes with seamless toggle and system preference detection.
   - Responsive layouts optimized for desktops, tablets, and small viewports.
   - High-contrast accessible color tokens for status badges and phase tags.

---

## Getting Started

### Prerequisites
- Node.js (v18+ recommended)
- npm or yarn

### Installation
From the repository root:
```bash
cd frontend
npm install
```

### Running Locally (Development Mode)
```bash
npm run dev
```
Open `http://localhost:5173` in your browser.

### Running Test Suite
Execute the Vitest component and unit test suite:
```bash
npm run test
```
Runs 15 automated unit and component integration tests verifying RFC 4180 parsing, metric calculations, and UI behavior.

### Building for Production
```bash
npm run build
```
Type-checks with `tsc -b` and bundles with Vite into `frontend/dist/`.

### Previewing Production Build
```bash
npm run preview
```

---

## File Structure

```
frontend/
├── public/
│   ├── default_output.csv       # Preloaded baseline output (518 cases)
│   └── favicon.svg              # Dashboard favicon
├── src/
│   ├── components/
│   │   ├── CaseDetailModal.tsx  # Step detail modal & raw JSON viewer
│   │   ├── CaseExplorer.tsx     # Filterable, sortable, paginated case table
│   │   ├── Header.tsx           # Navbar, dataset badge, theme toggle, file picker
│   │   ├── Overview.tsx         # Metric summary cards & distribution bar
│   │   └── ValidationBanner.tsx # Upload status & format warning notifications
│   ├── styles/
│   │   └── theme.css            # Dark/light CSS variables & utility classes
│   ├── test/
│   │   ├── components.test.tsx  # React Testing Library component tests
│   │   ├── csvParser.test.ts    # RFC 4180 parser edge-case tests
│   │   └── setup.ts             # Test runner setup
│   ├── types/
│   │   └── index.ts             # TypeScript domain models and interfaces
│   ├── utils/
│   │   ├── csvParser.ts         # Deterministic RFC 4180 streaming parser
│   │   └── stats.ts             # Summary metrics & phase aggregations
│   ├── App.tsx                  # Root application container & drag-drop handler
│   └── main.tsx                 # Entrypoint
├── package.json
├── tsconfig.app.json
├── vite.config.ts
└── README.md
```
