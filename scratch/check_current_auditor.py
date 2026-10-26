import sys, os
sys.path.insert(0, os.path.abspath('.'))
import csv, json
from datetime import datetime
from code.models import DeletionRequest, DeletionStatus
from code.auditor import DeletionAuditor

auditor = DeletionAuditor('dataset')
sample_reqs = [DeletionRequest.from_row(r) for r in csv.DictReader(open('dataset/sample_deletion_requests.csv', encoding='utf-8'))]

# Let's see what auditor currently predicts for the 32 cases
truth = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(open('dataset/sample_output.csv', encoding='utf-8'))}

matches = 0
for req in sample_reqs:
    pred = auditor.audit_case(req)
    exp_status, exp_steps = truth[req.case_id]
    pred_steps = [s.to_dict() if hasattr(s, 'to_dict') else s for s in pred.steps]
    if pred.deletion_status.value == exp_status and pred_steps == exp_steps:
        matches += 1
    else:
        print(f"Mismatch: {req.case_id} (Status: {pred.deletion_status.value == exp_status}, Steps: {len(pred_steps)} vs {len(exp_steps)})")

print(f"Current matches: {matches} / {len(sample_reqs)}")
