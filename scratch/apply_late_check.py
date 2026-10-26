import os

target_path = 'code/auditor.py'
with open(target_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_bonus = '''                    elif obs_for_act:
                        known_eids = {o.evidence_id for o in obs_list if o.evidence_id}
                        if any(o.evidence_id in known_eids for o in obs_for_act):
                            score -= 5000.0'''

new_bonus = '''                    elif obs_for_act:
                        known_eids = {o.evidence_id for o in obs_list if o.evidence_id}
                        # Only apply bundle evidence bonus if the case does not have late findings
                        if not any(anc > rep_at for anc in anchors):
                            if any(o.evidence_id in known_eids for o in obs_for_act):
                                score -= 5000.0'''

assert old_bonus in content, "old_bonus not found!"
content = content.replace(old_bonus, new_bonus, 1)

with open(target_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Applied late findings check to code/auditor.py")
