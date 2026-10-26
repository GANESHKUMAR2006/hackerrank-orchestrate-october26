import csv
from datetime import datetime

with open('dataset/sample_deletion_requests.csv', encoding='utf-8') as f:
    sample_requests = list(csv.DictReader(f))
with open('dataset/system_activity.csv', encoding='utf-8') as f:
    activities = [a for a in csv.DictReader(f) if a['source_system'] == 'deletion_worker']

for req in sample_requests[:6]:
    rep_at = datetime.fromisoformat(req['reported_at'].replace('Z', '+00:00'))
    req_at = datetime.fromisoformat(req['requested_at'].replace('Z', '+00:00'))
    matched = []
    for a in activities:
        ev_time = datetime.fromisoformat(a['event_time'].replace('Z', '+00:00'))
        if -7200 <= (ev_time - rep_at).total_seconds() <= 3600:
            matched.append(a)
    print(f"{req['case_id']} (RepAt: {req['reported_at']}): {len(matched)} activities")
    for m in matched:
        print(f"   {m['event_time']} | {m['target_system']} | {m['event_type']} | {m['resource_id']} | {m['reported_result']}")
