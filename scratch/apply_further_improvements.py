import os

target_path = 'code/auditor.py'
with open(target_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update outcome alignment and shared evidence bonus
old_block = '''                    # Outcome alignment bonus: check anchor activities and intake reported_status
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

new_block = '''                    # Outcome alignment bonus: prioritize intake reported_status over secondary anchor outcomes
                    is_complete_intake = (request.reported_status == "COMPLETE")
                    is_not_started = (request.reported_status == "NOT_STARTED")

                    if is_complete_intake:
                        if act.reported_result == "SUCCESS":
                            score -= 10000.0
                        else:
                            score += 10000.0
                    elif is_not_started:
                        if act.reported_result in {"FAILED", "PARTIAL"}:
                            score -= 10000.0
                        else:
                            score += 10000.0
                    elif "FAILED" in anchor_outcomes:
                        if act.reported_result in {"FAILED", "PARTIAL"}:
                            score -= 3600.0
                        else:
                            score += 10000.0
                    elif "SUCCESS" in anchor_outcomes:
                        if act.reported_result == "SUCCESS":
                            score -= 3600.0
                        else:
                            score += 10000.0

                    # Verified evidence bonus
                    obs_for_act = self.cache.get_observations_for_resource(act.resource_id)
                    has_user_match = any(
                        o.identifiers.get("email", "").lower() in req_emails
                        or (user_id and o.identifiers.get("user_id") == user_id)
                        for o in obs_for_act
                    )
                    if has_user_match:
                        score -= 10000.0
                    elif obs_for_act:
                        known_eids = {o.evidence_id for o in obs_list if o.evidence_id}
                        if any(o.evidence_id in known_eids for o in obs_for_act):
                            score -= 5000.0'''

assert old_block in content, "old_block not found!"
content = content.replace(old_block, new_block, 1)

# 2. Update analytics interest
old_analytics = '''        has_analytics_interest = (
            not explicitly_scoped and (
                "analytic" in req_lower or "statistic" in req_lower or "tracking" in req_lower or "metric" in req_lower
                or any(a.event_type == "DELETE_RECORD" for dt_a, a in job_acts if a.target_system == "analytics_platform")
                or "service_resource_export" in str([o.source_file for o in obs_list])
            )
        )'''

new_analytics = '''        has_analytics_interest = (
            not explicitly_scoped and (
                "analytic" in req_lower or "statistic" in req_lower or "tracking" in req_lower or "metric" in req_lower
                or any(a.event_type == "DELETE_RECORD" for dt_a, a in job_acts if a.target_system == "analytics_platform")
                or "service_resource_export" in str([o.source_file for o in obs_list])
                or ("resource_lookup_trace" in str([o.source_file for o in obs_list]) and request.reported_status == "COMPLETE")
            )
        )'''

assert old_analytics in content, "old_analytics not found!"
content = content.replace(old_analytics, new_analytics, 1)

with open(target_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated code/auditor.py successfully")
