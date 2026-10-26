import sys, os
sys.path.insert(0, os.path.abspath('.'))
import csv, json
from datetime import datetime
from code.identity import IdentityResolver

resolver = IdentityResolver(dataset_dir="dataset")
reqs = {r['case_id']: r for r in csv.DictReader(open('dataset/sample_deletion_requests.csv', encoding='utf-8'))}
acts = list(csv.DictReader(open('dataset/system_activity.csv', encoding='utf-8')))

for cid in ['case_18', 'case_20', 'case_23', 'case_27', 'case_29']:
    req = reqs[cid]
    email = req['email']
    req_dt = datetime.fromisoformat(req['requested_at'].replace('Z', '+00:00'))
    user = resolver.resolve(email, req_dt)
    user_id = user.user_id if user else None
    print(f"*** {cid} (email={email}, user_id={user_id}, reported_at={req.get('reported_at')}, reported_status={req.get('reported_status')}) ***")
    user_acts = [a for a in acts if a.get('user_id') == user_id or a.get('actor_id') == user_id]
    print(f"  user_acts count: {len(user_acts)}")
    for a in user_acts:
        print(f"    {a['timestamp']} | {a['system_id']} | {a['action']} | {a.get('resource_id')} | {a.get('status')}")
