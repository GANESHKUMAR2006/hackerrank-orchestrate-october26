import csv
import json
import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from code.auditor import DeletionAuditor
from code.evidence.cache import EvidenceCache
from code.classifier import RequestIntentClassifier
from code.identity import IdentityResolver
from code.planner import PolicyPlanner
from code.models import DeletionRequest

# Initialize components
cache = EvidenceCache()
cache.load_all_evidence()
classifier = RequestIntentClassifier()
resolver = IdentityResolver()
resolver.load_datasets("dataset/user_identities.csv", "dataset/user_audit_log.csv")
planner = PolicyPlanner()

auditor = DeletionAuditor(
    cache=cache,
    classifier=classifier,
    resolver=resolver,
    planner=planner,
    activity_csv_path="dataset/system_activity.csv",
)

# Load sample requests
with open("dataset/sample_deletion_requests.csv", encoding="utf-8") as f:
    sample_requests = [DeletionRequest.from_row(r) for r in csv.DictReader(f)]

with open("dataset/sample_output.csv", encoding="utf-8") as f:
    truth = {r["case_id"]: (r["deletion_status"], json.loads(r["steps_json"])) for r in csv.DictReader(f)}

# Run auditor
preds = [auditor.audit_case(req) for req in sample_requests]

# Evaluate
exact_matches = 0
for p in preds:
    cid = p.case_id
    t_st, t_steps = truth[cid]
    p_st = p.deletion_status.value
    p_steps = [s.to_dict() for s in p.audit_steps]
    st_m = (t_st == p_st)
    steps_m = (t_steps == p_steps)
    if steps_m:
        exact_matches += 1
    else:
        print(f"Mismatch {cid}: StatusMatch={st_m}, StepsMatch={steps_m}")
        print(f"  Truth ({len(t_steps)}):")
        for s in t_steps:
            print(f"    {s['phase']} | {s['system_id']} | {s['resource_id']} | {s['operation']} | {s['state']} | {s.get('evidence_id', '')}")
        print(f"  Pred ({len(p_steps)}):")
        for s in p_steps:
            print(f"    {s['phase']} | {s['system_id']} | {s['resource_id']} | {s['operation']} | {s['state']} | {s.get('evidence_id', '')}")
        print()

print(f"\nExact matches before edits: {exact_matches} / 32 ({exact_matches/32*100:.2f}%)")
