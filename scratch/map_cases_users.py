import csv, json

with open('dataset/sample_output.csv', 'r', encoding='utf-8') as f:
    truth = {row['case_id']: json.loads(row['steps_json']) for row in csv.DictReader(f)}

with open('dataset/user_identities.csv', 'r', encoding='utf-8') as f:
    users_by_email = {row['email']: row['user_id'] for row in csv.DictReader(f)}

with open('dataset/sample_deletion_requests.csv', 'r', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        cid = row['case_id']
        email = row['email']
        uid = users_by_email.get(email, 'UNKNOWN')
        sec = [s for s in truth[cid] if s['system_id'] == 'security_service']
        sec_id = sec[0]['resource_id'] if sec else 'NONE'
        sec_ev = sec[0]['evidence_id'] if sec else ''
        print(f"{cid:8s} {email:30s} {uid:10s} {sec_id:20s} {repr(sec_ev)}")
