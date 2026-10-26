import csv
import json
from datetime import datetime

with open('dataset/sample_deletion_requests.csv', encoding='utf-8') as f:
    sample_requests = list(csv.DictReader(f))
with open('dataset/sample_output.csv', encoding='utf-8') as f:
    truth = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(f)}
with open('dataset/system_activity.csv', encoding='utf-8') as f:
    activities = [a for a in csv.DictReader(f) if a['source_system'] == 'deletion_worker']

# Check how many truth resources appear in deletion_worker activities
total_truth_resources = 0
truth_in_activities = 0
truth_not_in_activities = []

for req in sample_requests:
    cid = req['case_id']
    t_st, t_steps = truth[cid]
    all_act_res = set(a['resource_id'] for a in activities)
    for s in t_steps:
        # Exclude security_service audit_records which are retained security logs
        if s['system_id'] == 'security_service':
            continue
        total_truth_resources += 1
        if s['resource_id'] in all_act_res:
            truth_in_activities += 1
        else:
            truth_not_in_activities.append((cid, s['system_id'], s['resource_id']))

print(f"Total non-security truth resources: {total_truth_resources}")
print(f"Found in deletion_worker activities: {truth_in_activities} ({truth_in_activities/total_truth_resources*100:.2f}%)")
print(f"Not in deletion_worker activities: {len(truth_not_in_activities)}")
for x in truth_not_in_activities:
    print("  ", x)
