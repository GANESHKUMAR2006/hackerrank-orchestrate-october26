import sys, os
sys.path.insert(0, os.path.abspath('.'))
from code.evidence.cache import EvidenceCache

cache = EvidenceCache('dataset')
cache.load_all_evidence()

all_obs = cache.get_all_observations()
audit_obs = [o for o in all_obs if o.system_id == 'security_service' or 'audit_record' in o.resource_id]

print(f"Total security/audit observations in cache: {len(audit_obs)}")
for o in audit_obs:
    if any(k in o.resource_id for k in ['6645', '5569']) or any(k in str(o.identifiers) for k in ['user_18', 'user_20', 'user_48', 'user_50', 'mori.ren', 'akosua.gyasi']):
        print(o.resource_id, o.evidence_id, o.source_file, o.identifiers)
