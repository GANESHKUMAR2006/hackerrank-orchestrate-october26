import csv
import json
import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from code.models import DeletionRequest
from code.auditor import DeletionAuditor

with open('dataset/sample_output.csv', 'r', encoding='utf-8') as f:
    r = csv.DictReader(f)
    truth = {row['case_id']: (row['deletion_status'], json.loads(row['steps_json'])) for row in r}

auditor = DeletionAuditor('dataset')
cases_to_check = ['case_18', 'case_20', 'case_23', 'case_25', 'case_26', 'case_29']

with open('dataset/sample_deletion_requests.csv', 'r', encoding='utf-8') as f:
    r = csv.DictReader(f)
    for row in r:
        if row['case_id'] in cases_to_check:
            req = DeletionRequest.from_row(row)
            pred = auditor.audit_case(req)
            t_status, t_steps = truth[req.case_id]
            pred_status = pred.deletion_status.value if hasattr(pred.deletion_status, 'value') else str(pred.deletion_status)
            print(f'=== {req.case_id} ===')
            print(f'Status: Pred={pred_status} Truth={t_status}')
            print('Pred steps:')
            for s in pred.steps:
                ph = s.phase.value if hasattr(s.phase, 'value') else s.phase
                op = s.operation.value if hasattr(s.operation, 'value') else s.operation
                st = s.state.value if hasattr(s.state, 'value') else s.state
                print(f'  {s.step_no} {ph} {s.system_id} {s.resource_id} {op} {st} {repr(s.evidence_id)}')
            print('Truth steps:')
            for s in t_steps:
                print(f"  {s['step_no']} {s['phase']} {s['system_id']} {s['resource_id']} {s['operation']} {s['state']} {repr(s['evidence_id'])}")
            print()
