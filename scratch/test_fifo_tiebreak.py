import sys, os
sys.path.insert(0, os.path.abspath('.'))
import csv, json
from code.models import DeletionRequest
from code.auditor import DeletionAuditor

auditor = DeletionAuditor('dataset')
sample_reqs = [DeletionRequest.from_row(r) for r in csv.DictReader(open('dataset/sample_deletion_requests.csv', encoding='utf-8'))]
truth = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(open('dataset/sample_output.csv', encoding='utf-8'))}

# Let's inspect case_23 and case_27 candidates
for cid in ['case_23', 'case_27']:
    req = [r for r in sample_reqs if r.case_id == cid][0]
    ug = auditor.resolver.resolve(req.email, as_of=req.audit_at).user_graph
    rep_at = req.reported_at
    req_at = req.requested_at
    job_acts = []
    for act in auditor.activities:
        if act.source_system == 'deletion_worker':
            delta_rep = (act.event_time - rep_at).total_seconds()
            delta_req = (act.event_time - req_at).total_seconds()
            if delta_req >= -3600 and -7200 <= delta_rep <= 7200:
                job_acts.append((act.event_time, act))
    obs_list = auditor.cache.get_observations_for_user(ug, cutoff=None)
    resources = {o.resource_id: o.system_id for o in obs_list if o.resource_id and o.system_id}
    anchors = [t for t, a in job_acts if a.resource_id in resources and a.target_system != 'security_service']
    
    print(f"=== {cid} ===")
    if cid == 'case_23':
        for dt_a, act in job_acts:
            if act.target_system == 'account_service' and act.event_type == 'DELETE_RECORD' and act.reported_result == 'FAILED':
                dist = min(abs((dt_a - anc).total_seconds()) for anc in anchors)
                print(f"  {act.resource_id} | dt={dt_a.isoformat()} | dist={dist}")
    elif cid == 'case_27':
        for dt_a, act in job_acts:
            if act.target_system == 'analytics_platform' and act.event_type in {'ANONYMIZE_RECORD', 'DELETE_RECORD'}:
                dist = min(abs((dt_a - anc).total_seconds()) for anc in anchors)
                print(f"  {act.resource_id} | dt={dt_a.isoformat()} | dist={dist}")
