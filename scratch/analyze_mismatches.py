import csv
import json
from datetime import datetime

with open('dataset/sample_deletion_requests.csv', encoding='utf-8') as f:
    requests = {r['case_id']: r for r in csv.DictReader(f)}
with open('dataset/sample_output.csv', encoding='utf-8') as f:
    truth = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(f)}
with open('tmp_sample_baseline.csv', encoding='utf-8') as f:
    pred = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(f)}
with open('dataset/system_activity.csv', encoding='utf-8') as f:
    activities = list(csv.DictReader(f))

mismatches = [
    'case_03', 'case_04', 'case_12', 'case_16', 'case_17', 'case_18',
    'case_20', 'case_21', 'case_22', 'case_23', 'case_25', 'case_26',
    'case_27', 'case_28', 'case_31', 'case_32'
]

for cid in mismatches:
    req = requests[cid]
    t_st, t_steps = truth[cid]
    p_st, p_steps = pred[cid]
    print(f"=== {cid} ===")
    print(f"Email: {req['email']}, ReqAt: {req['requested_at']}, RepAt: {req['reported_at']}, AuditAt: {req['audit_at']}")
    print(f"Truth Status: {t_st}")
    for s in t_steps:
        print(f"  [TRUTH] {s['phase']} | {s['system_id']} | {s['resource_id']} | {s['operation']} | {s['state']} | {s.get('evidence_id', '')}")
    print("  [PRED]")
    for s in p_steps:
        print(f"  [PRED]  {s['phase']} | {s['system_id']} | {s['resource_id']} | {s['operation']} | {s['state']} | {s.get('evidence_id', '')}")

    dt_rep = datetime.fromisoformat(req['reported_at'].replace('Z', '+00:00'))
    close_acts = []
    for a in activities:
        dt_a = datetime.fromisoformat(a['event_time'].replace('Z', '+00:00'))
        if abs((dt_a - dt_rep).total_seconds()) <= 7200:
            close_acts.append(a)
    print("  [CLOSE ACTIVITIES]")
    for a in close_acts:
        print(f"    {a['event_time']} | {a['source_system']} -> {a['target_system']} | {a['event_type']} | res: {a['resource_id']}")
    print()
