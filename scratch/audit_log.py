import re
import os
from datetime import datetime

log_path = 'log.txt'
if not os.path.exists(log_path):
    print("log.txt does not exist!")
    exit(1)

with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print(f"Total lines in log.txt: {len(lines)}")

# Let's find all headers: '## [TIMESTAMP] TITLE'
entries = []
current_entry = None

header_pattern = re.compile(r'^##\s+\[(.*?)\]\s+(.*)')

for i, line in enumerate(lines):
    m = header_pattern.match(line.strip())
    if m:
        if current_entry:
            entries.append(current_entry)
        current_entry = {
            'line_no': i + 1,
            'timestamp_str': m.group(1),
            'title': m.group(2),
            'lines': [line],
        }
    else:
        if current_entry:
            current_entry['lines'].append(line)

if current_entry:
    entries.append(current_entry)

print(f"Total entries found: {len(entries)}")

# 1. Check Timestamps: parsing and ordering
prev_dt = None
out_of_order = []
bad_timestamps = []

for idx, e in enumerate(entries):
    t_str = e['timestamp_str']
    dt = None
    # Try various ISO formats
    for fmt in [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S",
    ]:
        try:
            dt = datetime.strptime(t_str.replace("+00:00", "Z"), fmt)
            break
        except Exception:
            pass
    if not dt:
        try:
            dt = datetime.fromisoformat(t_str)
        except Exception:
            pass
    
    e['dt'] = dt
    if not dt:
        bad_timestamps.append((idx, e['line_no'], t_str, e['title']))
    else:
        if prev_dt and dt < prev_dt:
            out_of_order.append((idx, e['line_no'], t_str, prev_dt.isoformat(), e['title']))
        prev_dt = dt

print(f"\n--- 1. Timestamps ---")
print(f"Bad timestamps: {len(bad_timestamps)}")
for b in bad_timestamps:
    print(f"  Line {b[1]}: '{b[2]}' in '{b[3]}'")

print(f"Out of order timestamps: {len(out_of_order)}")
for o in out_of_order:
    print(f"  Line {o[1]} (entry {o[0]}): {o[2]} comes AFTER {o[3]} (title: '{o[4]}')")

# 2. Check Required Sections & Context fields
print(f"\n--- 2. Required Sections & Context Fields ---")
missing_sections = []
for idx, e in enumerate(entries):
    text = "".join(e['lines'])
    title = e['title']
    line_no = e['line_no']
    if "SESSION START" in title:
        # Session start requirements: tool=, model=, Repo Root:, Branch:, Worktree:, Parent Agent:, Language:
        req_fields = ["tool=", "model=", "Repo Root:", "Branch:", "Worktree:", "Language:"]
        missing = [f for f in req_fields if f.lower() not in text.lower()]
        if missing:
            missing_sections.append((idx, line_no, title, f"SESSION START missing: {missing}"))
    else:
        # Per turn requirements:
        # User Prompt (verbatim, secrets redacted):
        # Agent Response Summary:
        # Actions:
        # Context:
        # tool=, model=, branch=, repo_root=, worktree=, parent_agent=
        req_blocks = ["user prompt", "agent response summary", "actions:", "context:"]
        missing_b = [b for b in req_blocks if b not in text.lower()]
        
        req_ctx = ["tool=", "model=", "repo_root=", "branch=", "worktree="]
        missing_c = [c for c in req_ctx if c not in text.lower()]
        
        if missing_b or missing_c:
            missing_sections.append((idx, line_no, title, f"Blocks missing: {missing_b}, Context missing: {missing_c}"))

print(f"Entries with missing sections/fields: {len(missing_sections)}")
for m in missing_sections:
    print(f"  Line {m[1]} ({m[2]}): {m[3]}")

# 3. Check Repository Paths Consistency
print(f"\n--- 3. Repository Paths Consistency ---")
repo_roots = []
for idx, e in enumerate(entries):
    text = "".join(e['lines'])
    m_root = re.search(r'repo_root\s*=\s*(.*)', text, re.IGNORECASE)
    if not m_root:
        m_root = re.search(r'Repo Root:\s*(.*)', text)
    if m_root:
        path = m_root.group(1).strip()
        repo_roots.append((idx, e['line_no'], path))

unique_roots = set(r[2] for r in repo_roots)
print(f"Unique repo_root values found ({len(unique_roots)}):")
for u in unique_roots:
    count = sum(1 for r in repo_roots if r[2] == u)
    print(f"  '{u}' (count: {count})")

# 4. Check for potential accidental secrets
print(f"\n--- 4. Secret / Credential Scan ---")
secret_patterns = [
    re.compile(r'(?i)(api[_-]?key|secret|token|password|bearer|auth|credential)\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{16,})["\']?'),
    re.compile(r'ghp_[a-zA-Z0-9]{36}'),
    re.compile(r'AIza[0-9A-Za-z-_]{35}'),
    re.compile(r'sk-[a-zA-Z0-9]{20,}'),
]
potential_secrets = []
for idx, e in enumerate(entries):
    for line_idx, line in enumerate(e['lines']):
        for pat in secret_patterns:
            m = pat.search(line)
            if m:
                # ignore if redacted or placeholder
                val = m.group(0)
                if "[REDACTED]" not in val and "<" not in val and "None" not in val and "null" not in val and "sha256" not in val and "email_hash" not in val:
                    potential_secrets.append((idx, e['line_no'] + line_idx, val[:60]))

print(f"Potential secrets found: {len(potential_secrets)}")
for s in potential_secrets:
    print(f"  Line {s[1]}: {s[2]}")
