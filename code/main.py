"""Ghost Data Still Exists — Main Execution Pipeline.

Executes the deletion audit pipeline against deletion requests, reconstructing state
at audit_at, evaluating policy rules, generating remediation steps, and emitting
the compliant output CSV.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from typing import List, Tuple

# Ensure repository root is at index 0 of sys.path
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if sys.path[0] != _REPO_ROOT:
    sys.path.insert(0, _REPO_ROOT)

from code.auditor import DeletionAuditor
from code.models import CasePrediction, DeletionRequest, DeletionStatus


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ghost Data Still Exists — Automated Deletion Audit Agent"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default="dataset",
        help="Path to dataset directory containing manifest and CSV records (default: dataset)",
    )
    parser.add_argument(
        "--requests-file",
        type=str,
        default=None,
        help="Path to specific deletion requests CSV (default: {input-dir}/deletion_requests.csv)",
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default="output.csv",
        help="Path to destination output CSV file (default: output.csv)",
    )
    parser.add_argument(
        "--mode",
        choices=["full", "sample"],
        default="full",
        help="Run mode: 'full' for all 518 cases, 'sample' for 32 public sample cases (default: full)",
    )
    return parser.parse_args(argv)


def run_pipeline(
    input_dir: str = "dataset",
    requests_file: str | None = None,
    output_path: str = "output.csv",
    mode: str = "full",
) -> List[CasePrediction]:
    """Execute complete audit pipeline and write results to output_path."""
    start_time = time.time()

    # Determine requests file
    if requests_file is None:
        if mode == "sample":
            requests_path = os.path.join(input_dir, "sample_deletion_requests.csv")
        else:
            requests_path = os.path.join(input_dir, "deletion_requests.csv")
    else:
        requests_path = requests_file

    if not os.path.exists(requests_path):
        raise FileNotFoundError(f"Requests file not found at: {requests_path}")

    print(f"Loading deletion requests from: {requests_path}")
    with open(requests_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        requests = [DeletionRequest.from_row(row) for row in reader]

    # Ensure natural case_id sort order (e.g. case_01, case_02, ... case_550)
    def case_sort_key(r: DeletionRequest) -> Tuple[int, str]:
        parts = r.case_id.split("_")
        if len(parts) > 1 and parts[1].isdigit():
            return (int(parts[1]), r.case_id)
        return (999999, r.case_id)

    requests.sort(key=case_sort_key)
    print(f"Total requests to audit: {len(requests)}")

    # Initialize auditor and ingest evidence corpus
    print(f"Initializing DeletionAuditor with dataset directory: {input_dir}")
    auditor = DeletionAuditor(dataset_dir=input_dir)

    print("Executing state reconstruction and remediation planning...")
    predictions: List[CasePrediction] = []
    status_counts = {
        DeletionStatus.COMPLETE: 0,
        DeletionStatus.INCOMPLETE: 0,
        DeletionStatus.NOT_APPLICABLE: 0,
    }

    for i, req in enumerate(requests, start=1):
        pred = auditor.audit_case(req)
        predictions.append(pred)
        status_counts[pred.deletion_status] += 1

        if i % 100 == 0 or i == len(requests):
            elapsed = time.time() - start_time
            print(f"  Processed {i}/{len(requests)} cases ({elapsed:.1f}s)...")

    # Serialize to output CSV
    print(f"Writing {len(predictions)} predictions to: {output_path}")
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["case_id", "deletion_status", "steps_json"])
        for p in predictions:
            steps_str = json.dumps([s.to_dict() for s in p.steps], separators=(",", ":"))
            writer.writerow([p.case_id, p.deletion_status.value, steps_str])

    total_time = time.time() - start_time
    print(f"\nAudit complete in {total_time:.2f}s.")
    print("Decision summary:")
    print(f"  COMPLETE:       {status_counts[DeletionStatus.COMPLETE]}")
    print(f"  INCOMPLETE:     {status_counts[DeletionStatus.INCOMPLETE]}")
    print(f"  NOT_APPLICABLE: {status_counts[DeletionStatus.NOT_APPLICABLE]}")

    return predictions


def main() -> None:
    args = parse_args()
    run_pipeline(
        input_dir=args.input_dir,
        requests_file=args.requests_file,
        output_path=args.output_path,
        mode=args.mode,
    )


if __name__ == "__main__":
    main()
