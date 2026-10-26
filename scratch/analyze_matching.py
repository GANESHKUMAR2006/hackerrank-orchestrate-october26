import csv
import json
from datetime import datetime

with open('dataset/sample_deletion_requests.csv', encoding='utf-8') as f:
    sample_requests = list(csv.DictReader(f))
with open('dataset/sample_output.csv', encoding='utf-8') as f:
    truth = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(f)}
with open('dataset/system_activity.csv', encoding='utf-8') as f:
    activities = [a for a in csv.DictReader(f) if a['source_system'] == 'deletion_worker']

# Group requests by reported_at
by_reported_at = {}
for req in sample_requests:
    rep = req['reported_at']
    by_reported_at.setdefault(rep, []).append(req)

for rep, reqs in sorted(by_reported_at.items()):
    print(f"=== Reported At: {rep} ({len(reqs)} requests) ===")
    dt_rep = datetime.fromisoformat(rep.replace('Z', '+00:00'))
    
    # Activities within 2 hours before rep
    close_acts = []
    for a in activities:
        dt_a = datetime.fromisoformat(a['event_time'].replace('Z', '+00:00'))
        if -7200 <= (dt_a - dt_rep).total_seconds() <= 1800:
            close_acts.append(a)
    print(f"  Total deletion_worker activities: {len(close_acts)}")
    for a in close_acts:
        print(f"    {a['event_time']} | {a['target_system']:<20} | {a['event_type']:<20} | {a['resource_id']:<15} | {a['reported_result']}")
    print("  Requests and their truth resources:")
    for r in reqs:
        cid = r['case_id']
        t_st, t_steps = truth[cid]
        res = [s['system_id'] + ':' + s['resource_id'] for s in t_steps if s['system_id'] != 'security_service']
        print(f"    {cid} ({r['email']}): {res}")
    print()
