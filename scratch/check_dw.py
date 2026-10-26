import sys, os
sys.path.insert(0, os.path.abspath('.'))
import csv
from datetime import datetime

reqs = {r['case_id']: r for r in csv.DictReader(open('dataset/sample_deletion_requests.csv', encoding='utf-8'))}
acts = list(csv.DictReader(open('dataset/system_activity.csv', encoding='utf-8')))

for cid in ['case_23', 'case_29', 'case_18', 'case_20', 'case_27']:
    req = reqs[cid]
    rep_at = datetime.fromisoformat(req['reported_at'].replace('Z', '+00:00'))
    req_at = datetime.fromisoformat(req['requested_at'].replace('Z', '+00:00'))
    print(f"=== {cid} ===")
    print(f"requested_at: {req_at}, reported_at: {rep_at}, status: {req['reported_status']}")
    
    # find deletion_worker acts
    dw_acts = []
    for a in acts:
        if a['source_system'] == 'deletion_worker':
            et = datetime.fromisoformat(a['event_time'].replace('Z', '+00:00'))
            delta_rep = (et - rep_at).total_seconds()
            delta_req = (et - req_at).total_seconds()
            if abs(delta_rep) <= 14400 or abs(delta_req) <= 14400:
                dw_acts.append((et, delta_rep, a))
    
    dw_acts.sort(key=lambda x: x[0])
    for et, d_rep, a in dw_acts:
        print(f"  {et.isoformat()} (delta_rep={d_rep:6.0f}s) | target={a['target_system']:18s} | act={a['event_type']:16s} | res={a['resource_id']:15s} | res_res={a['reported_result']}")
