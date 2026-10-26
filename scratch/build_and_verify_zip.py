import os
import sys
import zipfile
import tempfile
import shutil
import subprocess

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ZIP_PATH = os.path.join(REPO_ROOT, "code.zip")

print(f"Building cross-platform submission ZIP: {ZIP_PATH}")

# Explicit exclusions
EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".git", "venv", ".venv", "dataset", "frontend", "scratch", "node_modules", "challenge-repo"}
EXCLUDE_EXTS = {".pyc", ".zip", ".tar", ".gz"}

entries_added = []

with zipfile.ZipFile(ZIP_PATH, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
    # 1. Add README.md and requirements.txt from root
    for root_file in ["README.md", "requirements.txt"]:
        rf_path = os.path.join(REPO_ROOT, root_file)
        if os.path.exists(rf_path):
            zinfo = zipfile.ZipInfo(root_file)
            zinfo.external_attr = 0o644 << 16
            with open(rf_path, "rb") as fp:
                zf.writestr(zinfo, fp.read())
            entries_added.append(root_file)

    # 2. Add everything under code/
    code_dir = os.path.join(REPO_ROOT, "code")
    for root, dirs, files in os.walk(code_dir):
        # In-place filter out excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            if any(f.endswith(ext) for ext in EXCLUDE_EXTS):
                continue
            abs_p = os.path.join(root, f)
            rel_p = os.path.relpath(abs_p, REPO_ROOT).replace("\\", "/")
            
            # Create POSIX ZipInfo to avoid Windows backslash artifacts
            zinfo = zipfile.ZipInfo(rel_p)
            zinfo.external_attr = 0o644 << 16
            with open(abs_p, "rb") as fp:
                zf.writestr(zinfo, fp.read())
            entries_added.append(rel_p)

print(f"Added {len(entries_added)} files to code.zip.")
for e in entries_added[:10]:
    print(f"  {e}")
print(f"  ... and {len(entries_added)-10} more.")

# Verify all paths have forward slashes
with zipfile.ZipFile(ZIP_PATH, "r") as zf:
    for name in zf.namelist():
        assert "\\" not in name, f"Backslash found in ZIP entry: {name}"
        assert not name.startswith("dataset/"), f"Dataset found in ZIP: {name}"
        assert not name.startswith("frontend/"), f"Frontend found in ZIP: {name}"
        assert "__pycache__" not in name, f"Pycache found in ZIP: {name}"

print("ZIP structure integrity verified: 100% forward slashes, no datasets/caches/frontends.")

# Extract to temporary directory and test execution
temp_dir = tempfile.mkdtemp(prefix="ghost_data_test_")
print(f"Extracting code.zip into temp directory: {temp_dir}")

try:
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        zf.extractall(temp_dir)
    
    # Copy dataset into temp_dir for test execution
    shutil.copytree(os.path.join(REPO_ROOT, "dataset"), os.path.join(temp_dir, "dataset"))
    
    # Run pytest inside temp_dir
    print("Running pytest in extracted directory...")
    res = subprocess.run([sys.executable, "-m", "pytest", "code/tests", "-v"], cwd=temp_dir, capture_output=True, text=True)
    print("Pytest stdout tail:")
    print("\n".join(res.stdout.strip().splitlines()[-5:]))
    assert res.returncode == 0, f"Pytest failed in extracted directory: {res.stderr}"

    # Run main.py in extracted directory
    print("Running code/main.py in extracted directory...")
    out_csv = os.path.join(temp_dir, "out_test.csv")
    res_main = subprocess.run([sys.executable, "code/main.py", "--mode", "sample", "--output-path", out_csv], cwd=temp_dir, capture_output=True, text=True)
    print(res_main.stdout.strip())
    assert res_main.returncode == 0, f"code/main.py failed in extracted directory: {res_main.stderr}"
    assert os.path.exists(out_csv), "out_test.csv was not produced!"

    print("All extracted execution tests passed successfully!")
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)

# Also sync code.zip to challenge-repo/code.zip if challenge-repo exists
chal_repo = os.path.join(REPO_ROOT, "challenge-repo")
if os.path.exists(chal_repo):
    shutil.copyfile(ZIP_PATH, os.path.join(chal_repo, "code.zip"))
    print("Synced code.zip to challenge-repo/code.zip")
