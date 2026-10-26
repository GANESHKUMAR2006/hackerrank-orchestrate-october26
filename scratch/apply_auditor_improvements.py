import os

target_path = 'code/auditor.py'
with open(target_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update account scoring
old_acct_scoring = '''                    score = 0.0
                    if anchor_time:
                        dist = abs((dt_a - anchor_time).total_seconds())
                        score += dist
                    else:
                        dist = abs((dt_a - rep_at).total_seconds())
                        score += dist

                    # Outcome alignment bonus
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

                    # Verified evidence bonus: prefer resources confirmed in evidence files
                    obs_for_act = self.cache.get_observations_for_resource(act.resource_id)
                    if obs_for_act and ("FAILED" not in anchor_outcomes or act.reported_result in {"FAILED", "PARTIAL"}):
                        score -= 10000.0'''

new_acct_scoring = '''                    score = 0.0
                    if anchors:
                        dist = min(abs((dt_a - anc).total_seconds()) for anc in anchors)
                    elif anchor_time:
                        dist = abs((dt_a - anchor_time).total_seconds())
                    else:
                        dist = abs((dt_a - rep_at).total_seconds())
                    score += dist

                    # Outcome alignment bonus: check anchor activities and intake reported_status
                    is_complete_intake = (request.reported_status == "COMPLETE")
                    is_failed_intake = (request.reported_status in {"NOT_STARTED", "INCOMPLETE"})

                    if "FAILED" in anchor_outcomes or is_failed_intake:
                        if act.reported_result in {"FAILED", "PARTIAL"}:
                            score -= 3600.0
                        else:
                            score += 10000.0
                    elif "SUCCESS" in anchor_outcomes or is_complete_intake:
                        if act.reported_result == "SUCCESS":
                            score -= 3600.0
                        else:
                            score += 10000.0

                    # Verified evidence bonus: only grant if observations specifically match user identity
                    obs_for_act = self.cache.get_observations_for_resource(act.resource_id)
                    has_user_match = any(
                        o.identifiers.get("email", "").lower() in req_emails
                        or (user_id and o.identifiers.get("user_id") == user_id)
                        for o in obs_for_act
                    )
                    if has_user_match:
                        score -= 10000.0'''

assert old_acct_scoring in content, "old_acct_scoring not found!"
content = content.replace(old_acct_scoring, new_acct_scoring, 1)

# 2. Narrow analytics interest
old_analytics_trace = '                or "resource_lookup_trace" in str([o.source_file for o in obs_list])\n'
assert old_analytics_trace in content, "old_analytics_trace not found!"
content = content.replace(old_analytics_trace, '', 1)

# 3. Add anchor recomputation after analytics
old_analytics_anchor = '''            if analytics_cands:
                analytics_cands.sort(key=lambda x: x[0])
                if analytics_cands[0][0] <= 5400:
                    resources[analytics_cands[0][1].resource_id] = "analytics_platform"'''

new_analytics_anchor = '''            if analytics_cands:
                analytics_cands.sort(key=lambda x: x[0])
                if analytics_cands[0][0] <= 5400:
                    resources[analytics_cands[0][1].resource_id] = "analytics_platform"
                    anchors = [t for t, a in job_acts if a.resource_id in resources and a.target_system != "security_service"]'''

assert old_analytics_anchor in content, "old_analytics_anchor not found!"
content = content.replace(old_analytics_anchor, new_analytics_anchor, 1)

# 4. Search cands cluster distance
old_search_dist = '''                    if anchor_time:
                        dist = abs((dt_a - anchor_time).total_seconds())
                    else:
                        dist = abs((dt_a - rep_at).total_seconds())'''

new_search_dist = '''                    if anchors:
                        dist = min(abs((dt_a - anc).total_seconds()) for anc in anchors)
                    elif anchor_time:
                        dist = abs((dt_a - anchor_time).total_seconds())
                    else:
                        dist = abs((dt_a - rep_at).total_seconds())'''

assert old_search_dist in content, "old_search_dist not found!"
content = content.replace(old_search_dist, new_search_dist, 1)

with open(target_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully applied improvements to code/auditor.py")
