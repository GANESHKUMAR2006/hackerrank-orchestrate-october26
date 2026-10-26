import csv
from datetime import datetime

with open('dataset/system_activity.csv', encoding='utf-8') as f:
    acts = [a for a in csv.DictReader(f) if a['source_system'] == 'deletion_worker']

print(f"Total deletion_worker activities: {len(acts)}")
# Print fields of an activity row
print("Fields:", list(acts[0].keys()))

# Check dates with multiple deletion worker activities
from collections import Counter
date_counts = Counter(a['event_time'][:10] for a in acts)
print("Top dates with deletion worker activities:")
for d, c in date_counts.most_common(10):
    print(f"  {d}: {c} activities")
