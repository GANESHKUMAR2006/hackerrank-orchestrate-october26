import csv
import json
from datetime import datetime

# Load all requests (sample + full)
with open('dataset/deletion_requests.csv', encoding='utf-8') as f:
    full_reqs = list(csv.DictReader(f))
with open('dataset/sample_deletion_requests.csv', encoding='utf-8') as f:
    sample_reqs = list(csv.DictReader(f))

# Merge requests by case_id
all_reqs_dict = {r['case_id']: r for r in full_reqs}
for r in sample_reqs:
    all_reqs_dict[r['case_id']] = r
all_reqs = list(all_reqs_dict.values())

with open('dataset/sample_output.csv', encoding='utf-8') as f:
    truth = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(f)}

with open('dataset/system_activity.csv', encoding='utf-8') as f:
    dw_acts = [a for a in csv.DictReader(f) if a['source_system'] == 'deletion_worker']

# Group all requests by reported_at
by_reported_at = {}
for r in all_reqs:
    by_reported_at.setdefault(r['reported_at'], []).append(r)

# Check sample cases
correct_account = 0
total_sample_cases = 0

for rep, reqs in sorted(by_reported_at.items()):
    dt_rep = datetime.fromisoformat(rep.replace('Z', '+00:00'))
    
    # Get all account DELETE_RECORD activities in [-2h, +30m]
    acts = []
    for a in dw_acts:
        if a['target_system'] == 'account_service' and a['event_type'] == 'DELETE_RECORD':
            dt_a = datetime.fromisoformat(a['event_time'].replace('Z', '+00:00'))
            if -7200 <= (dt_a - dt_rep).total_seconds() <= 1800:
                acts.append((dt_a, a))
    acts.sort(key=lambda x: x[0])
    act_objs = [x[1] for x in acts]
    
    # Sort reqs by requested_at then case_id
    reqs.sort(key=lambda x: (x['requested_at'], int(x['case_id'].split('_')[1])))
    
    sample_in_batch = [r for r in reqs if r['case_id'] in truth]
    if sample_in_batch:
        print(f"=== RepAt {rep} (Total reqs: {len(reqs)}, Total acct acts: {len(act_objs)}) ===")
        for idx, r in enumerate(reqs):
            assigned_act = act_objs[idx]['resource_id'] if idx < len(act_objs) else "NONE"
            cid = r['case_id']
            if cid in truth:
                t_st, t_steps = truth[cid]
                t_acct = [s['resource_id'] for s in t_steps if s['system_id'] == 'account_service']
                t_acct_str = t_acct[0] if t_acct else "NONE"
                is_match = (assigned_act == t_acct_str)
                print(f"  Req {cid} ({r['email']}): assigned {assigned_act} | truth {t_acct_str} | Match: {is_match}")
                total_sample_cases += 1
                if is_match:
                    correct_account += 1
        print()

print(f"Overall Account Match Accuracy: {correct_account} / {total_sample_cases} ({correct_account/total_sample_cases*100:.2f}%)")
