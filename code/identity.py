"""Deterministic identity graph resolution and historical alias reconstruction.

Resolves request emails against current identities (user_identities.csv) and
historical audit entries (user_audit_log.csv). Preserves audit IDs for citation
and strictly prevents false joins across shared names or non-unique attributes.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import os
from typing import Dict, List, Optional, Set

from code.evidence.parsers.csv_parser import CSVDatasetParser
from code.models import UserAuditEntry, UserIdentity, UserIdentityGraph


class IdentityResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    CONFLICTING = "CONFLICTING"


@dataclass
class AliasRecord:
    """Historical timeline entry for an identity attribute with provenance."""
    value: str
    field_name: str  # "email", "phone", "name", "email_hash"
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    audit_id: Optional[str] = None
    is_current: bool = False


@dataclass
class IdentityResolutionResult:
    """Result of identity graph resolution for a requested email."""
    status: IdentityResolutionStatus
    request_email: str
    user_id: Optional[str]
    user_graph: Optional[UserIdentityGraph]
    alias_history: List[AliasRecord] = field(default_factory=list)
    audit_ids: List[str] = field(default_factory=list)
    conflicting_user_ids: List[str] = field(default_factory=list)
    explanation: str = ""


class IdentityResolver:
    """Indexes identities and historical audit logs to reconstruct full subject identity graphs."""

    def __init__(self, dataset_dir: str = "dataset") -> None:
        self.dataset_dir = dataset_dir

        self.identities: List[UserIdentity] = []
        self.audit_entries: List[UserAuditEntry] = []

        # Indexes
        self._identities_by_email: Dict[str, List[UserIdentity]] = defaultdict(list)
        self._identities_by_user_id: Dict[str, UserIdentity] = {}

        self._audit_by_old_email: Dict[str, List[UserAuditEntry]] = defaultdict(list)
        self._audit_by_new_email: Dict[str, List[UserAuditEntry]] = defaultdict(list)
        self._audit_by_user_id: Dict[str, List[UserAuditEntry]] = defaultdict(list)

        self._is_loaded = False

    def load_datasets(
        self,
        identities_path: Optional[str] = None,
        audit_path: Optional[str] = None,
    ) -> None:
        """Load and index user_identities.csv and user_audit_log.csv."""
        id_path = identities_path or os.path.join(self.dataset_dir, "user_identities.csv")
        aud_path = audit_path or os.path.join(self.dataset_dir, "user_audit_log.csv")

        if os.path.exists(id_path):
            self.identities = CSVDatasetParser.parse_user_identities(id_path)
            self._identities_by_email.clear()
            self._identities_by_user_id.clear()
            for ident in self.identities:
                if ident.email:
                    self._identities_by_email[ident.email.lower()].append(ident)
                if ident.user_id:
                    self._identities_by_user_id[ident.user_id] = ident

        if os.path.exists(aud_path):
            self.audit_entries = CSVDatasetParser.parse_user_audit_log(aud_path)
            self._audit_by_old_email.clear()
            self._audit_by_new_email.clear()
            self._audit_by_user_id.clear()
            for entry in self.audit_entries:
                self._audit_by_user_id[entry.user_id].append(entry)
                if entry.field_name == "email":
                    if entry.old_value:
                        self._audit_by_old_email[entry.old_value.lower()].append(entry)
                    if entry.new_value:
                        self._audit_by_new_email[entry.new_value.lower()].append(entry)

        self._is_loaded = True

    def resolve(
        self,
        request_email: str,
        as_of: Optional[datetime] = None,
    ) -> IdentityResolutionResult:
        """Resolve a requested email into a complete UserIdentityGraph and alias history."""
        if not self._is_loaded:
            self.load_datasets()

        clean_email = (request_email or "").strip().lower()
        if not clean_email:
            return IdentityResolutionResult(
                status=IdentityResolutionStatus.UNRESOLVED,
                request_email=clean_email,
                user_id=None,
                user_graph=None,
                explanation="Empty request email provided.",
            )

        candidate_user_ids: Set[str] = set()

        # Step 1: Check current identities
        current_matches = self._identities_by_email.get(clean_email, [])
        for cm in current_matches:
            candidate_user_ids.add(cm.user_id)

        # Step 2: Check historical audit log (email changes)
        historical_matches = self._audit_by_old_email.get(clean_email, [])
        for hm in historical_matches:
            # If as_of is specified, verify historical change occurred before as_of
            if as_of is None or hm.event_time <= as_of:
                candidate_user_ids.add(hm.user_id)

        # Check for conflicts across multiple distinct user_ids
        if len(candidate_user_ids) > 1:
            return IdentityResolutionResult(
                status=IdentityResolutionStatus.CONFLICTING,
                request_email=clean_email,
                user_id=None,
                user_graph=None,
                conflicting_user_ids=sorted(list(candidate_user_ids)),
                explanation=f"Email {clean_email} maps to multiple conflicting user IDs: {candidate_user_ids}",
            )

        if not candidate_user_ids:
            return IdentityResolutionResult(
                status=IdentityResolutionStatus.UNRESOLVED,
                request_email=clean_email,
                user_id=None,
                user_graph=None,
                explanation=f"Email {clean_email} could not be resolved in identities or historical audit logs.",
            )

        # Unique user_id resolved
        user_id = next(iter(candidate_user_ids))
        current_ident = self._identities_by_user_id.get(user_id)
        user_audit_entries = self._audit_by_user_id.get(user_id, [])

        # Filter audit entries by as_of if specified
        if as_of is not None:
            user_audit_entries = [e for e in user_audit_entries if e.event_time <= as_of]

        # Sort audit entries chronologically
        user_audit_entries.sort(key=lambda x: x.event_time)

        # Reconstruct identity graph and timeline
        names: Set[str] = set()
        emails: Set[str] = set()
        phones: Set[str] = set()
        hashes: Set[str] = set()
        audit_ids: List[str] = []
        alias_history: List[AliasRecord] = []

        if current_ident:
            if current_ident.name:
                names.add(current_ident.name)
            if current_ident.email:
                emails.add(current_ident.email.lower())
                alias_history.append(
                    AliasRecord(
                        value=current_ident.email.lower(),
                        field_name="email",
                        valid_from=current_ident.updated_at,
                        is_current=True,
                    )
                )
            if current_ident.phone:
                phones.add(current_ident.phone)
                alias_history.append(
                    AliasRecord(
                        value=current_ident.phone,
                        field_name="phone",
                        valid_from=current_ident.updated_at,
                        is_current=True,
                    )
                )
            if current_ident.email_hash:
                hashes.add(current_ident.email_hash)

        # Ingest historical audit changes
        for entry in user_audit_entries:
            audit_ids.append(entry.audit_id)
            if entry.field_name == "email":
                if entry.old_value:
                    old_email = entry.old_value.strip().lower()
                    emails.add(old_email)
                    alias_history.append(
                        AliasRecord(
                            value=old_email,
                            field_name="email",
                            valid_to=entry.event_time,
                            audit_id=entry.audit_id,
                            is_current=False,
                        )
                    )
                if entry.new_value:
                    emails.add(entry.new_value.strip().lower())

            elif entry.field_name == "phone":
                if entry.old_value:
                    phones.add(entry.old_value.strip())
                    alias_history.append(
                        AliasRecord(
                            value=entry.old_value.strip(),
                            field_name="phone",
                            valid_to=entry.event_time,
                            audit_id=entry.audit_id,
                            is_current=False,
                        )
                    )
                if entry.new_value:
                    phones.add(entry.new_value.strip())

            elif entry.field_name == "email_hash":
                if entry.old_value:
                    hashes.add(entry.old_value.strip())
                if entry.new_value:
                    hashes.add(entry.new_value.strip())

        # Also add the requested email itself to emails set
        emails.add(clean_email)

        user_graph = UserIdentityGraph(
            user_id=user_id,
            names=names,
            emails=emails,
            phones=phones,
            email_hashes=hashes,
            audit_ids=audit_ids,
        )

        return IdentityResolutionResult(
            status=IdentityResolutionStatus.RESOLVED,
            request_email=clean_email,
            user_id=user_id,
            user_graph=user_graph,
            alias_history=alias_history,
            audit_ids=audit_ids,
            explanation=f"Successfully resolved to {user_id} with {len(emails)} email aliases and {len(audit_ids)} audit entries.",
        )
