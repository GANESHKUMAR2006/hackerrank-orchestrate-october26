import sys, os
sys.path.insert(0, os.path.abspath('.'))
import csv
from code.models import DeletionRequest
from code.auditor import DeletionAuditor

auditor = DeletionAuditor('dataset')
req27 = DeletionRequest.from_row(list(csv.DictReader(open('dataset/sample_deletion_requests.csv', encoding='utf-8')))[26]) # 27
user_graph = auditor.resolver.resolve(req27.email, as_of=req27.audit_at).user_graph
obs_list = auditor.cache.get_observations_for_user(user_graph, cutoff=None)
print("case_27 direct observations:")
for o in obs_list:
    print(f"  {o.system_id:20s} {o.resource_id:15s} {o.evidence_id} {o.source_file}")
