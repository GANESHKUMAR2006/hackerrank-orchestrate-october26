import sys, os
sys.path.insert(0, os.path.abspath('.'))
import csv
from datetime import datetime
from code.models import DeletionRequest
from code.auditor import DeletionAuditor

auditor = DeletionAuditor('dataset')
reqs = {r['case_id']: DeletionRequest.from_row(r) for r in csv.DictReader(open('dataset/sample_deletion_requests.csv', encoding='utf-8'))}

for cid in ['case_23', 'case_29', 'case_18', 'case_20', 'case_27']:
    req = reqs[cid]
    rep_at = req.reported_at
    req_at = req.requested_at
    
    # Simulate job_acts with -7200 <= delta_rep <= 7200
    job_acts = []
    for act in auditor.activities:
        if act.source_system == "deletion_worker":
            delta_rep = (act.event_time - rep_at).total_seconds()
            delta_req = (act.event_time - req_at).total_seconds()
            if delta_req >= -3600 and -7200 <= delta_rep <= 7200:
                job_acts.append((act.event_time, act))
                
    user_graph = auditor.resolver.resolve(req.email, as_of=req.audit_at).user_graph
    # Discover initial resources from evidence
    obs_list = auditor.cache.get_observations_for_user(user_graph, cutoff=None)
    resources = {o.resource_id: o.system_id for o in obs_list if o.resource_id and o.system_id}
    
    anchors = [t for t, a in job_acts if a.resource_id in resources and a.target_system != "security_service"]
    anchor_outcomes = [a.reported_result for t, a in job_acts if a.resource_id in resources and a.target_system != "security_service"]
    
    print(f"=== {cid} ===")
    print(f"  initial resources: {resources}")
    print(f"  anchors count: {len(anchors)}, outcomes: {anchor_outcomes}")
    
    # Test candidate account selection
    candidates = []
    req_emails = user_graph.emails if user_graph else {req.email.lower()}
    user_id = user_graph.user_id if user_graph else None
    for dt_a, act in job_acts:
        if act.target_system == "account_service" and act.event_type == "DELETE_RECORD":
            owner = auditor.evidence_user_map.get(act.resource_id)
            if owner and owner not in req_emails and owner != user_id:
                continue
            if anchors:
                dist = min(abs((dt_a - anc).total_seconds()) for anc in anchors)
            else:
                dist = abs((dt_a - rep_at).total_seconds())
            score = dist
            if anchor_outcomes:
                if "FAILED" in anchor_outcomes:
                    if act.reported_result in {"FAILED", "PARTIAL"}:
                        score -= 3600.0
                    else:
                        score += 10000.0
                elif "SUCCESS" in anchor_outcomes:
                    if act.reported_result == "SUCCESS":
                        score -= 3600.0
                    else:
                        score += 10000.0
            obs_for_act = auditor.cache.get_observations_for_resource(act.resource_id)
            has_user_match = any(o.identifiers.get('email', '').lower() in req_emails or o.identifiers.get('user_id') == user_id for o in obs_for_act)
            if has_user_match:
                score -= 10000.0
            candidates.append((score, act.resource_id, act.reported_result, dt_a.isoformat()))
            
    candidates.sort(key=lambda x: x[0])
    print("  top 3 account candidates:")
    for c in candidates[:3]:
        print(f"    score={c[0]:8.1f} | {c[1]:15s} | {c[2]:8s} | {c[3]}")
