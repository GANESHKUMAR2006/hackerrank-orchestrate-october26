import csv
import json
from datetime import datetime

with open('dataset/sample_output.csv', encoding='utf-8') as f:
    truth = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(f)}
with open('dataset/sample_deletion_requests.csv', encoding='utf-8') as f:
    requests = list(csv.DictReader(f))
with open('dataset/system_activity.csv', encoding='utf-8') as f:
    activities = [a for a in csv.DictReader(f) if a['source_system'] == 'deletion_worker']

import sys; sys.path.insert(0, '.')
from code.evidence.cache import EvidenceCache
from code.identity import IdentityResolver

cache = EvidenceCache()
cache.load_all_evidence()
resolver = IdentityResolver()
resolver.load_datasets('dataset/user_identities.csv', 'dataset/user_audit_log.csv')

evidence_user_map = {}
for obs in cache.get_all_observations():
    if obs.resource_id:
        if obs.identifiers.get('email'):
            evidence_user_map[obs.resource_id] = obs.identifiers['email'].lower()
        elif obs.identifiers.get('user_id'):
            evidence_user_map[obs.resource_id] = obs.identifiers['user_id']

# Group activities by resource
acts_by_res = {}
for a in activities:
    acts_by_res.setdefault(a['resource_id'], []).append(a)

for cid in ['case_18', 'case_20', 'case_21', 'case_23', 'case_31', 'case_32', 'case_28', 'case_25', 'case_26']:
    req = [r for r in requests if r['case_id'] == cid][0]
    email = req['email'].lower()
    res_obj = resolver.resolve(email)
    ug = res_obj.user_graph
    
    t_st, t_steps = truth[cid]
    t_acct = [s['resource_id'] for s in t_steps if s['system_id'] == 'account_service'][0]
    
    rep_at = datetime.fromisoformat(req['reported_at'].replace('Z', '+00:00'))
    req_at = datetime.fromisoformat(req['requested_at'].replace('Z', '+00:00'))
    
    # Direct evidence obs
    obs = cache.get_observations_for_user(ug, cutoff=None)
    obs = [o for o in obs if o.extracted_state != 'NOT_EXTRACTED' and 'resource_lookup_trace_202603' not in o.source_file]
    
    known_res = set(o.resource_id for o in obs if o.resource_id)
    anchor_acts = []
    for r in known_res:
        anchor_acts.extend(acts_by_res.get(r, []))
    anchor_res_types = [a['reported_result'] for a in anchor_acts if a['source_system'] == 'deletion_worker']
    print(f"=== {cid} ({email}) | Truth Acct: {t_acct} ===")
    print(f"  Known resources: {known_res}")
    print(f"  Anchor activities: {[(a['target_system'], a['resource_id'], a['reported_result']) for a in anchor_acts]}")
    
    # Candidate accounts in window
    acct_cands = []
    for a in activities:
        if a['target_system'] == 'account_service' and a['event_type'] == 'DELETE_RECORD':
            dt_a = datetime.fromisoformat(a['event_time'].replace('Z', '+00:00'))
            if -7200 <= (dt_a - rep_at).total_seconds() <= 1800 and (dt_a - req_at).total_seconds() >= -3600:
                owner = evidence_user_map.get(a['resource_id'])
                if owner and owner not in (ug.emails if ug else {email}) and owner != (ug.user_id if ug else None):
                    continue
                acct_cands.append(a)
    print(f"  Candidate accounts: {[(a['resource_id'], a['event_time'], a['reported_result']) for a in acct_cands]}")
    print()
