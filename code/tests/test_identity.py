"""Unit tests for IdentityResolver using synthetic test fixtures."""

from datetime import datetime, timezone
import os
import tempfile
import pytest

from code.identity import (
    IdentityResolutionStatus,
    IdentityResolver,
)


@pytest.fixture
def synthetic_identity_env():
    """Create synthetic identities and audit logs with edge cases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        id_path = os.path.join(tmpdir, "user_identities.csv")
        with open(id_path, "w", encoding="utf-8") as f:
            f.write("user_id,name,email,phone,email_hash,updated_at\n")
            f.write("user_100,Alice Walker,alice.walker@example.com,+1 555 0101,hash_100,2026-05-01T10:00:00Z\n")
            f.write("user_200,Bob Smith,bob.smith@example.com,+1 555 0202,hash_200,2026-05-01T10:00:00Z\n")
            # Shared name and phone between user_301 and user_302 (family landline & common name)
            f.write("user_301,Charlie Brown,charlie.first@example.com,+1 555 9999,hash_301,2026-05-01T10:00:00Z\n")
            f.write("user_302,Charlie Brown,charlie.second@example.com,+1 555 9999,hash_302,2026-05-01T10:00:00Z\n")

        aud_path = os.path.join(tmpdir, "user_audit_log.csv")
        with open(aud_path, "w", encoding="utf-8") as f:
            f.write("audit_id,user_id,event_time,field_name,old_value,new_value\n")
            # Alice changed her email from alice_old@example.com to alice.walker@example.com
            f.write("audit_901,user_100,2025-10-01T12:00:00Z,email,alice_old@example.com,alice.walker@example.com\n")
            f.write("audit_902,user_100,2025-10-01T12:00:00Z,phone,+1 555 0000,+1 555 0101\n")
            # Conflicting entry: two users claiming the same conflict email in history
            f.write("audit_998,user_100,2024-01-01T10:00:00Z,email,conflict@example.com,alice_old@example.com\n")
            f.write("audit_999,user_200,2024-01-01T10:00:00Z,email,conflict@example.com,bob.smith@example.com\n")

        resolver = IdentityResolver(dataset_dir=tmpdir)
        resolver.load_datasets(identities_path=id_path, audit_path=aud_path)
        yield resolver


def test_resolve_current_email(synthetic_identity_env):
    res = synthetic_identity_env.resolve("alice.walker@example.com")
    assert res.status == IdentityResolutionStatus.RESOLVED
    assert res.user_id == "user_100"
    assert res.user_graph is not None

    # Graph contains both current and historical aliases
    assert res.user_graph.matches("alice.walker@example.com")
    assert res.user_graph.matches("alice_old@example.com")
    assert res.user_graph.matches("+1 555 0101")
    assert res.user_graph.matches("+1 555 0000")
    assert "audit_901" in res.audit_ids


def test_resolve_historical_email(synthetic_identity_env):
    # Query using old email address
    res = synthetic_identity_env.resolve("alice_old@example.com")
    assert res.status == IdentityResolutionStatus.RESOLVED
    assert res.user_id == "user_100"
    assert res.user_graph is not None

    # Resolves to primary user_100 and connects current email
    assert res.user_graph.matches("alice.walker@example.com")
    assert "audit_901" in res.audit_ids
    assert any(a.value == "alice_old@example.com" and a.audit_id == "audit_901" for a in res.alias_history)


def test_no_false_joins_on_shared_names_or_phones(synthetic_identity_env):
    # user_301 and user_302 share name 'Charlie Brown' and phone '+1 555 9999'
    res1 = synthetic_identity_env.resolve("charlie.first@example.com")
    res2 = synthetic_identity_env.resolve("charlie.second@example.com")

    assert res1.status == IdentityResolutionStatus.RESOLVED
    assert res1.user_id == "user_301"

    assert res2.status == IdentityResolutionStatus.RESOLVED
    assert res2.user_id == "user_302"

    # user_301 must NOT match user_302 email or user_id
    assert not res1.user_graph.matches("charlie.second@example.com")
    assert not res1.user_graph.matches("user_302")

    # user_302 must NOT match user_301 email or user_id
    assert not res2.user_graph.matches("charlie.first@example.com")
    assert not res2.user_graph.matches("user_301")


def test_conflicting_identities(synthetic_identity_env):
    res = synthetic_identity_env.resolve("conflict@example.com")
    assert res.status == IdentityResolutionStatus.CONFLICTING
    assert res.user_id is None
    assert "user_100" in res.conflicting_user_ids
    assert "user_200" in res.conflicting_user_ids


def test_unknown_email(synthetic_identity_env):
    res = synthetic_identity_env.resolve("completely.unknown@example.com")
    assert res.status == IdentityResolutionStatus.UNRESOLVED
    assert res.user_id is None
    assert res.user_graph is None


def test_timestamp_boundary_resolution(synthetic_identity_env):
    # As of 2025-01-01 (before Alice changed email on 2025-10-01)
    as_of_before = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    res_before = synthetic_identity_env.resolve("alice.walker@example.com", as_of=as_of_before)
    # The current identity is in user_identities, but audit entries after 2025-01-01 are filtered
    assert res_before.status == IdentityResolutionStatus.RESOLVED
    assert "audit_901" not in res_before.audit_ids
