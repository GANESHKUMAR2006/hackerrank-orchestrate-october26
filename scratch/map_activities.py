import csv
import json
from datetime import datetime

with open('dataset/sample_deletion_requests.csv', encoding='utf-8') as f:
    sample_requests = list(csv.DictReader(f))
with open('dataset/sample_output.csv', encoding='utf-8') as f:
    truth = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(f)}
with open('dataset/system_activity.csv', encoding='utf-8') as f:
    activities = [a for a in csv.DictReader(f) if a['source_system'] == 'deletion_worker']

for req in sample_requests:
    cid = req['case_id']
    t_st, t_steps = truth[cid]
    t_resources = {s['system_id']: s['resource_id'] for s in t_steps}
    
    rep_at = datetime.fromisoformat(req['reported_at'].replace('Z', '+00:00'))
    req_at = datetime.fromisoformat(req['requested_at'].replace('Z', '+00:00'))
    
    # Find activities in window
    acts_in_window = []
    for a in activities:
        ev_t = datetime.fromisoformat(a['event_time'].replace('Z', '+00:00'))
        # Window: between requested_at and reported_at + 1h
        if (ev_t - req_at).total_seconds() >= -3600 and (ev_t - rep_at).total_seconds() <= 3600:
            acts_in_window.append(a)
            
    print(f"Case {cid} | {req['email']} | Req: {req['requested_at']} | Rep: {req['reported_at']}")
    print(f"  Truth resources: {t_resources}")
    matched_acts = [a for a in acts_in_window if a['resource_id'] in t_resources.values()]
    print(f"  Acts matching truth ({len(matched_acts)}): {[a['resource_id'] for a in matched_acts]}")
    other_acts = [a for a in acts_in_window if a['resource_id'] not in t_resources.values()]
    print(f"  Other acts in window ({len(other_acts)}): {[a['target_system'] + ':' + a['resource_id'] for a in other_acts]}")
    print()
