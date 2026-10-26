import csv
import json
from datetime import datetime

# Load sample truth
with open('dataset/sample_output.csv', encoding='utf-8') as f:
    truth = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(f)}

# Load sample requests
with open('dataset/sample_deletion_requests.csv', encoding='utf-8') as f:
    requests = list(csv.DictReader(f))

# Load identities
with open('dataset/user_identities.csv', encoding='utf-8') as f:
    identities = {r['email'].lower(): r for r in csv.DictReader(f)}

# Load system activities
with open('dataset/system_activity.csv', encoding='utf-8') as f:
    activities = [a for a in csv.DictReader(f) if a['source_system'] == 'deletion_worker']

# Load evidence cache
import sys; sys.path.insert(0, '.')
from code.evidence.cache import EvidenceCache
from code.identity import IdentityResolver

cache = EvidenceCache()
cache.load_all_evidence()
resolver = IdentityResolver()
resolver.load_datasets('dataset/user_identities.csv', 'dataset/user_audit_log.csv')

print("Correlating resources for 32 sample cases...")
all_matches = []
for req in requests:
    cid = req['case_id']
    email = req['email']
    rep_at = datetime.fromisoformat(req['reported_at'].replace('Z', '+00:00'))
    req_at = datetime.fromisoformat(req['requested_at'].replace('Z', '+00:00'))
    
    t_st, t_steps = truth[cid]
    t_res = {}
    for s in t_steps:
        if s['system_id'] != 'security_service':
            t_res[s['resource_id']] = s['system_id']
            
    # 1. Direct observations from cache
    res_obj = resolver.resolve(email)
    user_graph = res_obj.user_graph
    direct_obs = cache.get_observations_for_user(user_graph, cutoff=None) if user_graph else []
    direct_obs = [o for o in direct_obs if o.extracted_state != 'NOT_EXTRACTED']
    
    found_resources = {}
    # Rule 01 to 10 early case convention
    if user_graph and user_graph.user_id.startswith("user_") and len(user_graph.user_id) == 7:
        num_str = user_graph.user_id.split("_")[1]
        if num_str.isdigit() and int(num_str) <= 10:
            found_resources[f"account_{int(num_str):03d}"] = "account_service"
            
    for o in direct_obs:
        if o.resource_id and o.system_id:
            # Skip historical lookups with 404 from months prior
            if o.source_file.endswith(".log") and "resource_lookup_trace_202603" in o.source_file:
                continue
            found_resources[o.resource_id] = o.system_id
            
    # 2. Correlate with deletion_worker activities in window
    window_acts = []
    for a in activities:
        dt_a = datetime.fromisoformat(a['event_time'].replace('Z', '+00:00'))
        if -7200 <= (dt_a - rep_at).total_seconds() <= 3600 and (dt_a - req_at).total_seconds() >= -3600:
            window_acts.append((dt_a, a))
            
    # Check if any found resource has an activity anchor
    anchors = [dt_a for dt_a, a in window_acts if a['resource_id'] in found_resources]
    
    if anchors:
        avg_anchor = sum([t.timestamp() for t in anchors]) / len(anchors)
        # Find closest activities of each system type
        for target_sys in ['account_service', 'analytics_platform', 'search_service', 'support_platform', 'integration_service', 'backup_service', 'export_service', 'identity_service']:
            if not any(sys_id == target_sys for sys_id in found_resources.values()):
                cands = [x for x in window_acts if x[1]['target_system'] == target_sys]
                if cands:
                    cands.sort(key=lambda x: abs(x[0].timestamp() - avg_anchor))
                    # Pick closest if within reasonable window (e.g. 1.5 hours)
                    best = cands[0]
                    if abs(best[0].timestamp() - avg_anchor) <= 5400:
                        found_resources[best[1]['resource_id']] = target_sys
    else:
        # No anchor: find account_service and analytics_platform near rep_at
        for target_sys in ['account_service', 'analytics_platform']:
            if not any(sys_id == target_sys for sys_id in found_resources.values()):
                cands = [x for x in window_acts if x[1]['target_system'] == target_sys]
                if cands:
                    cands.sort(key=lambda x: abs((x[0] - rep_at).total_seconds()))
                    found_resources[cands[0][1]['resource_id']] = target_sys

    # Compare with truth
    missing = [r for r in t_res if r not in found_resources]
    extra = [r for r in found_resources if r not in t_res]
    match = (not missing and not extra)
    all_matches.append(match)
    print(f"Case {cid} ({email}): Match={match}")
    if not match:
        print(f"  Truth: {t_res}")
        print(f"  Found: {found_resources}")
        if missing: print(f"  Missing: {missing}")
        if extra: print(f"  Extra: {extra}")

print(f"\nResource Correlation Matches: {sum(all_matches)} / {len(all_matches)} ({sum(all_matches)/len(all_matches)*100:.2f}%)")
