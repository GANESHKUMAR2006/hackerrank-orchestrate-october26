"""Temporal boundary enforcement for evidence and audit decisions.

Under the Ghost Data Still Exists specification, evidence or events captured
strictly after a request's audit_at timestamp cannot be cited or used to
determine the historical state for that case.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from code.models import EvidenceManifestEntry, EvidenceObservation


def is_temporally_valid(
    timestamp: Optional[datetime],
    cutoff: datetime,
) -> bool:
    """Return True if timestamp is on or before the cutoff time.

    If timestamp is None, it is assumed timeless or already bounded by file capture time.
    """
    if timestamp is None:
        return True
    return timestamp <= cutoff


def is_observation_temporally_valid(
    obs: EvidenceObservation,
    cutoff: datetime,
) -> bool:
    """Return True only if BOTH the observation timestamp and file capture time are <= cutoff."""
    if obs.file_captured_at is not None and obs.file_captured_at > cutoff:
        return False
    if obs.timestamp is not None and obs.timestamp > cutoff:
        return False
    return True


def filter_manifest_by_cutoff(
    manifest_entries: List[EvidenceManifestEntry],
    cutoff: datetime,
) -> List[EvidenceManifestEntry]:
    """Filter evidence manifest entries so only files captured on or before cutoff are retained."""
    return [entry for entry in manifest_entries if entry.captured_at <= cutoff]


def filter_observations_by_cutoff(
    observations: List[EvidenceObservation],
    cutoff: datetime,
) -> List[EvidenceObservation]:
    """Filter observations so only those occurring on or before cutoff are returned."""
    return [obs for obs in observations if is_observation_temporally_valid(obs, cutoff)]
