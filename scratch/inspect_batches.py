import csv
from datetime import datetime

with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    acts = list(csv.DictReader(f))

# Look at activities on 2026-09-09
print("=== Activities on 2026-09-09 ===")
for a in acts:
    if '2026-09-09' in a['event_time']:
        print(a['event_time'], a['source_system'], a['target_system'], a['event_type'], a['resource_id'], a['reported_result'], a['details'])

print("\n=== Activities on 2026-09-05 ===")
for a in acts:
    if '2026-09-05' in a['event_time']:
        print(a['event_time'], a['source_system'], a['target_system'], a['event_type'], a['resource_id'], a['reported_result'], a['details'])

print("\n=== Activities on 2026-08-30 ===")
for a in acts:
    if '2026-08-30' in a['event_time']:
        print(a['event_time'], a['source_system'], a['target_system'], a['event_type'], a['resource_id'], a['reported_result'], a['details'])
