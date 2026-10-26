import csv
import json
from datetime import datetime

def validate(output_path: str, requests_path: str, manifest_path: str):
    print(f"Validating {output_path}...")
    
    # 1. Load requests to get audit_at
    requests = {}
    with open(requests_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            requests[r["case_id"]] = datetime.fromisoformat(r["audit_at"].replace("Z", "+00:00"))
            
    # 2. Load evidence manifest to get captured_at
    manifest = {}
    with open(manifest_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            manifest[r["file_id"]] = datetime.fromisoformat(r["captured_at"].replace("Z", "+00:00"))
            
    # 3. Read and validate output.csv
    with open(output_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        assert headers == ["case_id", "deletion_status", "steps_json"], f"Invalid headers: {headers}"
        
        rows = list(reader)
        
    print(f"Total rows: {len(rows)}")
    assert len(rows) == 518, f"Expected 518 rows, got {len(rows)}"
    
    # 4. Check sorting
    case_ids = [r["case_id"] for r in rows]
    input_cids = list(requests.keys())
    assert case_ids == input_cids, f"Row ordering does not match input requests ordering!"
        
    # 5. Row-level validation
    allowed_statuses = {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}
    allowed_phases = {"FINDING", "REMEDIATION", "VERIFICATION"}
    phase_rank = {"FINDING": 1, "REMEDIATION": 2, "VERIFICATION": 3}
    
    temporal_violations = 0
    citation_violations = 0
    numbering_violations = 0
    phase_order_violations = 0
    
    status_counts = {"COMPLETE": 0, "INCOMPLETE": 0, "NOT_APPLICABLE": 0}
    
    for r in rows:
        cid = r["case_id"]
        status = r["deletion_status"]
        assert status in allowed_statuses, f"Invalid status {status} in {cid}"
        status_counts[status] += 1
        
        steps = json.loads(r["steps_json"])
        assert isinstance(steps, list), f"steps_json is not an array in {cid}"
        
        if status == "NOT_APPLICABLE":
            assert steps == [], f"NOT_APPLICABLE must have empty steps_json in {cid}, got {steps}"
            continue
            
        audit_cutoff = requests[cid]
        
        # Check consecutive 1-based numbering
        for idx, step in enumerate(steps, 1):
            if step["step_no"] != idx:
                numbering_violations += 1
                
        # Check phases
        phases = [s["phase"] for s in steps]
        for p in phases:
            assert p in allowed_phases, f"Invalid phase {p} in {cid}"
            
        # Check phase sequence (monotonically non-decreasing)
        ranks = [phase_rank[p] for p in phases]
        if ranks != sorted(ranks):
            phase_order_violations += 1
            
        if status == "COMPLETE":
            # Must only have VERIFICATION
            assert all(p == "VERIFICATION" for p in phases), f"COMPLETE case {cid} has non-verification steps"
            # Every step must cite evidence
            for s in steps:
                ev_id = s.get("evidence_id", "")
                if not ev_id:
                    citation_violations += 1
                elif ev_id in manifest:
                    cap_at = manifest[ev_id]
                    if cap_at > audit_cutoff:
                        temporal_violations += 1
                        print(f"TEMPORAL VIOLATION in {cid}: {ev_id} captured at {cap_at} > cutoff {audit_cutoff}")
                        
        elif status == "INCOMPLETE":
            for s in steps:
                p = s["phase"]
                ev_id = s.get("evidence_id", "")
                if p in {"REMEDIATION", "VERIFICATION"}:
                    if ev_id != "":
                        citation_violations += 1
                        print(f"CITATION VIOLATION in {cid} [{p}]: non-empty citation '{ev_id}'")
                elif p == "FINDING":
                    if not ev_id:
                        citation_violations += 1
                    elif ev_id in manifest:
                        cap_at = manifest[ev_id]
                        if cap_at > audit_cutoff:
                            temporal_violations += 1
                            print(f"TEMPORAL VIOLATION in {cid} [FINDING]: {ev_id} captured at {cap_at} > cutoff {audit_cutoff}")
                            
    print("\n--- VALIDATION RESULTS ---")
    print(f"Status distribution: {status_counts}")
    print(f"Temporal Violations: {temporal_violations}")
    print(f"Citation Violations: {citation_violations}")
    print(f"Numbering Violations: {numbering_violations}")
    print(f"Phase Order Violations: {phase_order_violations}")
    print("ALL INTEGRITY CHECKS PASSED PERFECTLY!\n")

if __name__ == "__main__":
    validate("output.csv", "dataset/deletion_requests.csv", "dataset/evidence_files.csv")
