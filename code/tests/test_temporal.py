"""Unit tests for code/evidence/temporal.py."""

from datetime import datetime, timezone
import pytest

from code.evidence.temporal import (
    filter_manifest_by_cutoff,
    filter_observations_by_cutoff,
    is_temporally_valid,
)
from code.models import EvidenceManifestEntry, EvidenceObservation


def test_is_temporally_valid():
    cutoff = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)

    # Exactly at cutoff
    assert is_temporally_valid(datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc), cutoff)
    # Strictly before cutoff
    assert is_temporally_valid(datetime(2026, 9, 15, 11, 59, 59, tzinfo=timezone.utc), cutoff)
    assert is_temporally_valid(datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc), cutoff)

    # Strictly after cutoff
    assert not is_temporally_valid(datetime(2026, 9, 15, 12, 0, 1, tzinfo=timezone.utc), cutoff)
    assert not is_temporally_valid(datetime(2026, 9, 16, 0, 0, tzinfo=timezone.utc), cutoff)

    # None timestamp is treated as timeless
    assert is_temporally_valid(None, cutoff)


def test_filter_manifest_by_cutoff():
    cutoff = datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc)
    entries = [
        EvidenceManifestEntry(
            file_id="ev_01",
            file_path="evidence/logs/log1.log",
            origin="sys1",
            captured_at=datetime(2026, 8, 20, 0, 0, tzinfo=timezone.utc),
        ),
        EvidenceManifestEntry(
            file_id="ev_02",
            file_path="evidence/logs/log2.log",
            origin="sys2",
            captured_at=datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc),
        ),
        EvidenceManifestEntry(
            file_id="ev_03",
            file_path="evidence/logs/log3.log",
            origin="sys3",
            captured_at=datetime(2026, 9, 2, 0, 0, tzinfo=timezone.utc),
        ),
    ]

    filtered = filter_manifest_by_cutoff(entries, cutoff)
    assert len(filtered) == 2
    assert {e.file_id for e in filtered} == {"ev_01", "ev_02"}


def test_filter_observations_by_cutoff():
    cutoff = datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc)
    obs1 = EvidenceObservation(
        source_file="f1",
        evidence_id="ev1",
        timestamp=datetime(2026, 9, 10, 9, 59, tzinfo=timezone.utc),
        system_id="sys",
        resource_id="res1",
        data_category="cat",
        extracted_state="PRESENT",
    )
    obs2 = EvidenceObservation(
        source_file="f2",
        evidence_id="ev2",
        timestamp=datetime(2026, 9, 10, 10, 1, tzinfo=timezone.utc),
        system_id="sys",
        resource_id="res2",
        data_category="cat",
        extracted_state="PRESENT",
    )
    obs3 = EvidenceObservation(
        source_file="f3",
        evidence_id="ev3",
        timestamp=None,
        system_id="sys",
        resource_id="res3",
        data_category="cat",
        extracted_state="PRESENT",
    )

    filtered = filter_observations_by_cutoff([obs1, obs2, obs3], cutoff)
    assert len(filtered) == 2
    assert obs1 in filtered
    assert obs3 in filtered
    assert obs2 not in filtered
