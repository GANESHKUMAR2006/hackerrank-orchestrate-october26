import sys, os
sys.path.insert(0, os.path.abspath('.'))
from code.evidence.cache import EvidenceCache

cache = EvidenceCache('dataset')
cache.load_all_evidence()

print(f"Total warnings: {len(cache.warnings)}")
for w in cache.warnings[:20]:
    print(w)

obs_by_file = {}
for o in cache.get_all_observations():
    obs_by_file.setdefault(o.evidence_id, []).append(o)

for entry in cache.manifest:
    count = len(obs_by_file.get(entry.file_id, []))
    if count == 0:
        print(f"Zero observations parsed from: {entry.file_id} ({entry.file_path})")
