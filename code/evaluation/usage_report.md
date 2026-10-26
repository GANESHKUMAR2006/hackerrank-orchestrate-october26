# Ghost Data Still Exists — Usage & Model Report

## 1. Overview and Operational Architecture

The **Ghost Data Still Exists** deletion audit agent was designed as an ultra-reliable, deterministic, explainable rule-and-evidence engine. All core functions—including multilingual intent classification, timestamp-aware identity resolution, multi-format evidence ingestion, state reconstruction, replication drift detection, and remediation planning—execute locally without reliance on external remote LLM API calls.

---

## 2. Model Usage & Resource Consumption

| Metric | Measured Value | Notes |
| :--- | :--- | :--- |
| **Model Provider** | None / Local Deterministic Engine | All processing executes in-process |
| **Model Name** | Deterministic Intent & Policy Engine | Rules & heuristics in `code/classifier.py` |
| **Total Model API Calls** | 0 | Zero external network calls made |
| **Total Input Tokens** | 0 | No remote token consumption |
| **Total Output Tokens** | 0 | No remote token generation |
| **Average Tokens / Request**| 0.0 tokens | Deterministic local evaluation |
| **Estimated Model Cost** | \$0.00 USD | \$0.00 incurred |
| **Total Execution Latency** | ~14.8s (Unit Tests) / ~1.9s (Full 518-Case Run) | High-throughput in-memory execution |

---

## 3. Image & Document Extraction

- **PDF Documents**: Parsed locally via `PyMuPDF` (`fitz`), extracting clean structured tabular and textual metadata without external OCR or vision APIs.
- **SQL Snapshots**: Ingested into isolated, in-memory SQLite instances (`sqlite3.connect(":memory:")`), extracting schema, table rows, and replication checkpoints.
- **Console Screenshots**: Metadata extracted locally; visual contents retained with `extracted_state = "NOT_EXTRACTED"` per the pluggable vision interface specification, strictly preventing fabricated findings.
