"""Unit tests for EvidenceCache indexing, querying, and error handling."""

from datetime import datetime, timezone
import json
import os
import tempfile
import pytest

from code.evidence.cache import EvidenceCache
from code.models import UserIdentityGraph


@pytest.fixture
def temp_cache_env():
    """Create a temporary dataset environment with manifest and synthetic files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        evidence_dir = os.path.join(tmpdir, "evidence")
        os.makedirs(evidence_dir, exist_ok=True)

        # 1. Manifest
        manifest_path = os.path.join(tmpdir, "evidence_files.csv")
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write("file_id,file_path,origin,captured_at\n")
            f.write("ev_json,evidence/data.json,system_export,2026-08-15T12:00:00Z\n")
            f.write("ev_txt,evidence/handover.txt,shift_ops,2026-09-01T12:00:00Z\n")
            f.write("ev_missing,evidence/non_existent.log,observability,2026-09-01T12:00:00Z\n")

        # 2. JSON file with multi-alias data
        json_path = os.path.join(evidence_dir, "data.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "exported_at": "2026-08-15T12:00:00Z",
                "service_exports": {
                    "account_service": {
                        "profile_lookups": [
                            {"resource_id": "acc_01", "status_code": 404, "profile": None},
                            {"resource_id": "acc_02", "status_code": 200, "profile": {"email": "alias1@example.com", "user_id": "user_42"}},
                        ]
                    }
                }
            }, f)

        # 3. TXT file
        txt_path = os.path.join(evidence_dir, "handover.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("- 2026-09-01T12:00:00Z | search_service | search_02 | SEARCH_INDEX_ENTRY | FOUND | alias2@example.com\n")
            f.write("- 2026-09-01T12:00:00Z | backup_service | bak_02 | BACKUP_ARCHIVE | BLOCKED | user_42\n")

        yield tmpdir


def test_cache_loading_and_missing_file_warning(temp_cache_env):
    cache = EvidenceCache(dataset_dir=temp_cache_env)
    cache.load_all_evidence()

    # Total observations from existing files: acc_01, acc_02, search_02, bak_02 = 4
    all_obs = cache.get_all_observations()
    assert len(all_obs) == 4

    # Structured warning logged for ev_missing without terminating
    assert any(w.warning_type == "FILE_NOT_FOUND" and w.file_id == "ev_missing" for w in cache.warnings)


def test_cache_query_by_user_identity_graph(temp_cache_env):
    cache = EvidenceCache(dataset_dir=temp_cache_env)
    cache.load_all_evidence()

    # User with multiple aliases: primary email, secondary alias, and user_id
    user_graph = UserIdentityGraph(
        user_id="user_42",
        emails={"alias1@example.com", "alias2@example.com"},
    )

    # Cutoff after all files
    cutoff = datetime(2026, 9, 10, 0, 0, tzinfo=timezone.utc)
    user_obs = cache.get_observations_for_user(user_graph, cutoff=cutoff)

    # Should find acc_02 (email alias1 / user_42), search_02 (alias2), and bak_02 (user_42)
    res_ids = {o.resource_id for o in user_obs}
    assert res_ids == {"acc_02", "search_02", "bak_02"}


def test_cache_temporal_cutoff_enforcement(temp_cache_env):
    cache = EvidenceCache(dataset_dir=temp_cache_env)
    cache.load_all_evidence()

    user_graph = UserIdentityGraph(
        user_id="user_42",
        emails={"alias1@example.com", "alias2@example.com"},
    )

    # Cutoff between JSON (2026-08-15) and TXT (2026-09-01)
    cutoff = datetime(2026, 8, 20, 0, 0, tzinfo=timezone.utc)
    user_obs = cache.get_observations_for_user(user_graph, cutoff=cutoff)

    # Only acc_02 from JSON should be included
    res_ids = {o.resource_id for o in user_obs}
    assert res_ids == {"acc_02"}
    assert "search_02" not in res_ids
    assert "bak_02" not in res_ids


def test_cache_reuse_without_reload(temp_cache_env):
    cache = EvidenceCache(dataset_dir=temp_cache_env)
    cache.load_all_evidence()
    first_obs_count = len(cache.get_all_observations())

    # Call again, should return instantly from memory
    cache.load_all_evidence()
    assert len(cache.get_all_observations()) == first_obs_count
