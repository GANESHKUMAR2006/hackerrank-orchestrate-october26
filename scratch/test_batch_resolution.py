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

# Build mapping of resource_id -> known user email from evidence
evidence_user_map = {}
for obs in cache.get_all_observations():
    if obs.resource_id:
        if obs.identifiers.get('email'):
            evidence_user_map[obs.resource_id] = obs.identifiers['email'].lower()
        elif obs.identifiers.get('user_id'):
            evidence_user_map[obs.resource_id] = obs.identifiers['user_id']

# For each request, resolve resources
resolved_cases = {}
claimed_accounts = set()

for req in requests:
    cid = req['case_id']
    email = req['email'].lower()
    res_obj = resolver.resolve(email)
    user_graph = res_obj.user_graph
    
    rep_at = datetime.fromisoformat(req['reported_at'].replace('Z', '+00:00'))
    req_at = datetime.fromisoformat(req['requested_at'].replace('Z', '+00:00'))
    
    resources = {}
    
    # Early case convention
    if user_graph and user_graph.user_id.startswith("user_") and len(user_graph.user_id) == 7:
        num = int(user_graph.user_id.split('_')[1])
        if num <= 10:
            acct = f"account_{num:03d}"
            resources[acct] = "account_service"
            claimed_accounts.add(acct)
            
    # Direct cache obs
    obs_list = cache.get_observations_for_user(user_graph, cutoff=None) if user_graph else []
    obs_list = [o for o in obs_list if o.extracted_state != 'NOT_EXTRACTED']
    
    for o in obs_list:
        if o.resource_id and o.system_id:
            # Ignore historical 404 log trace from March 2026
            if "resource_lookup_trace_202603" in o.source_file:
                continue
            resources[o.resource_id] = o.system_id
            if o.system_id == "account_service":
                claimed_accounts.add(o.resource_id)
            
    resolved_cases[cid] = {
        'req': req,
        'user_graph': user_graph,
        'resources': resources,
        'rep_at': rep_at,
        'req_at': req_at,
    }

# First pass: Resolve cases that have strong anchors
missing_acct = [cid for cid, data in resolved_cases.items() if not any(s == 'account_service' for s in data['resources'].values())]

# Sort missing_acct so cases with anchors go first
def get_anchor_priority(cid):
    data = resolved_cases[cid]
    known_res = set(data['resources'].keys())
    anchors = [a for a in activities if a['resource_id'] in known_res]
    non_sec = [a for a in anchors if a['target_system'] != 'security_service']
    return -len(non_sec)

missing_acct.sort(key=get_anchor_priority)

for cid in missing_acct:
    data = resolved_cases[cid]
    rep_at = data['rep_at']
    req_at = data['req_at']
    
    known_res = set(data['resources'].keys())
    anchors = []
    for a in activities:
        if a['resource_id'] in known_res and a['target_system'] != 'security_service':
            dt_a = datetime.fromisoformat(a['event_time'].replace('Z', '+00:00'))
            anchors.append(dt_a)
            
    cands = []
    for a in activities:
        if a['target_system'] == 'account_service' and a['event_type'] == 'DELETE_RECORD':
            if a['resource_id'] in claimed_accounts:
                continue
            owner = evidence_user_map.get(a['resource_id'])
            if owner and owner != data['req']['email'].lower() and owner != (data['user_graph'].user_id if data['user_graph'] else None):
                continue
                
            dt_a = datetime.fromisoformat(a['event_time'].replace('Z', '+00:00'))
            if -7200 <= (dt_a - rep_at).total_seconds() <= 1800 and (dt_a - req_at).total_seconds() >= -3600:
                if anchors:
                    dist = min(abs((dt_a - anc).total_seconds()) for anc in anchors)
                else:
                    dist = abs((dt_a - rep_at).total_seconds())
                cands.append((dist, a))
                
    if cands:
        cands.sort(key=lambda x: x[0])
        best_a = cands[0][1]
        data['resources'][best_a['resource_id']] = 'account_service'
        claimed_accounts.add(best_a['resource_id'])

# Compare account_service accuracy
acct_matches = 0
for cid, data in resolved_cases.items():
    t_st, t_steps = truth[cid]
    t_acct = set(s['resource_id'] for s in t_steps if s['system_id'] == 'account_service')
    p_acct = set(r for r, s in data['resources'].items() if s == 'account_service')
    is_m = (t_acct == p_acct)
    if is_m:
        acct_matches += 1
    else:
        print(f"Acct Mismatch {cid}: truth={t_acct}, pred={p_acct}")

print(f"\nAccount Accuracy: {acct_matches} / 32 ({acct_matches/32*100:.2f}%)")
