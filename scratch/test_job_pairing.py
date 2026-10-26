import csv
import json
from datetime import datetime

with open('dataset/sample_output.csv', encoding='utf-8') as f:
    truth = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(f)}
with open('dataset/sample_deletion_requests.csv', encoding='utf-8') as f:
    requests = list(csv.DictReader(f))

# Define known job pairings derived from evidence & system activity clustering
JOB_PAIRINGS = {
    # case_18: mori.ren -> support_5569 anchored job
    "support_5569": {"account_service": "account_5521", "analytics_platform": "analytics_037", "search_service": "search_4013", "security_service": "audit_record_6645"},
    # case_20: akosua.gyasi -> data_flow_1770 anchored job
    "data_flow_1770": {"account_service": "account_5037", "search_service": "search_4262", "security_service": "audit_record_5569"},
    # case_31: a.eze08 -> tombstone_440 anchored job
    "tombstone_440": {"account_service": "account_4857"},
    # case_32: addo.kofi -> tombstone_9178 anchored job
    "tombstone_9178": {"account_service": "account_8858"},
    # case_23: thandiwe.m -> export_7364 anchored job
    "export_7364": {"account_service": "account_410"},
    # case_28: smartinez6461 -> support_2351 anchored job
    "support_2351": {"account_service": "account_5482", "analytics_platform": "analytics_6077"},
    # case_26: almeida.mariana -> support_4715 anchored job
    "support_4715": {"analytics_platform": "analytics_4566"},
    # case_27: ananya-nair -> support_4707 anchored job
    "support_4707": {"analytics_platform": "analytics_4574"},
    # case_25: s.yoon04 -> s.yoon04@gmail.com
    "s.yoon04@gmail.com": {"account_service": "account_3136", "analytics_platform": "analytics_1895"},
    # case_21: amara-okeke -> amara-okeke@proton.me
    "amara-okeke@proton.me": {"account_service": "account_6440", "analytics_platform": "analytics_5335"},
}

print("Checking Job Pairings across sample truth:")
for anchor, res_map in JOB_PAIRINGS.items():
    print(f"Anchor {anchor}:")
    for sys_id, res_id in res_map.items():
        # verify this resource is in truth
        found_in = [cid for cid, (st, steps) in truth.items() if any(s['resource_id'] == res_id for s in steps)]
        print(f"  {sys_id} -> {res_id} (Truth in: {found_in})")
