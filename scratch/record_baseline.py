import os
import csv
import json
import zipfile
import subprocess
import sys

print("=== PHASE 1: BASELINE INVENTORY ===")

# 1. output.csv
out_path = "output.csv"
if os.path.exists(out_path):
    with open(out_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    status_counts = {}
    for r in rows:
        st = r.get("deletion_status", "")
        status_counts[st] = status_counts.get(st, 0) + 1
    print(f"output.csv: exists=True, rows={len(rows)}, fieldnames={fieldnames}, status_dist={status_counts}")
else:
    print("output.csv: exists=False")

# 2. code.zip
zip_path = "code.zip"
if os.path.exists(zip_path):
    size_kb = os.path.getsize(zip_path) / 1024
    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
    has_backslash = any("\\" in n for n in namelist)
    has_dataset = any("dataset" in n for n in namelist)
    has_pycache = any("__pycache__" in n for n in namelist)
    print(f"code.zip: exists=True, size={size_kb:.1f}KB, total_files={len(namelist)}, backslashes={has_backslash}, dataset={has_dataset}, pycache={has_pycache}")
else:
    print("code.zip: exists=False")

# 3. log.txt
log_path = "log.txt"
if os.path.exists(log_path):
    with open(log_path, mode="r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    entries = [l for l in lines if l.startswith("## [")]
    print(f"log.txt: exists=True, lines={len(lines)}, turn_headers={len(entries)}")
else:
    print("log.txt: exists=False")

# 4. Evaluation reports
eval_rep = "code/evaluation/evaluation_report.md"
usage_rep = "code/evaluation/usage_report.md"
print(f"evaluation_report.md: exists={os.path.exists(eval_rep)}")
print(f"usage_report.md: exists={os.path.exists(usage_rep)}")

# 5. Run Python tests
print("Running Python tests (pytest code/tests -v)...")
res = subprocess.run([sys.executable, "-m", "pytest", "code/tests", "-q"], capture_output=True, text=True)
print("Pytest output:", res.stdout.strip())
print("Pytest exit code:", res.returncode)

# 6. Run public sample evaluation
print("Running public sample evaluation...")
eval_res = subprocess.run([sys.executable, "code/evaluation/main.py", "--prediction-path", "tmp_sample_baseline.csv", "--truth-path", "dataset/sample_output.csv"], capture_output=True, text=True)
print("Evaluation output summary:")
for line in eval_res.stdout.splitlines():
    if "Accuracy" in line or "Match" in line or "Violations" in line or "Cases" in line:
        print("  ", line.strip())

# 7. Frontend tests
print("Running frontend tests...")
fe_res = subprocess.run(["npm", "test"], cwd="frontend", shell=True, capture_output=True, text=True)
print("Frontend test stdout tail:")
print("\n".join(fe_res.stdout.strip().splitlines()[-5:]))
print("Frontend exit code:", fe_res.returncode)
