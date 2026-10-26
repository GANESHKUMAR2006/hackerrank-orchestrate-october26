import sys, os
sys.path.insert(0, os.path.abspath('.'))
import csv
from code.models import DeletionRequest
from code.auditor import DeletionAuditor

auditor = DeletionAuditor('dataset')
reqs = {r['case_id']: DeletionRequest.from_row(r) for r in csv.DictReader(open('dataset/sample_deletion_requests.csv', encoding='utf-8'))}

for cid in ['case_27', 'case_28', 'case_29', 'case_23', 'case_18']:
    req = reqs[cid]
    id_res = auditor.resolver.resolve(req.email, as_of=req.audit_at)
    user_graph = id_res.user_graph
    res = auditor._discover_resources(req, user_graph)
    print(f"=== {cid} ===")
    for rid, sid in sorted(res.items(), key=lambda x: x[1]):
        print(f"  {sid:20s}: {rid}")
