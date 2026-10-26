"""Evidence cache providing single-pass multi-format ingestion and indexed querying."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import os
from typing import Dict, List, Optional, Set, Tuple

from code.evidence.parsers.base import BaseEvidenceParser
from code.evidence.parsers.csv_parser import CSVDatasetParser
from code.evidence.parsers.image_parser import ImageEvidenceParser, ImageExtractor
from code.evidence.parsers.json_parser import JSONEvidenceParser
from code.evidence.parsers.log_parser import LogEvidenceParser
from code.evidence.parsers.pdf_parser import PDFEvidenceParser
from code.evidence.parsers.sql_parser import SQLEvidenceParser
from code.evidence.parsers.txt_parser import TextEvidenceParser
from code.evidence.temporal import is_observation_temporally_valid
from code.models import EvidenceManifestEntry, EvidenceObservation, IngestionWarning, SystemActivity, UserIdentityGraph


class EvidenceCache:
    """Ingests and indexes all multi-format evidence once, enabling fast filtered lookups."""

    def __init__(self, dataset_dir: str = "dataset", image_extractor: Optional[ImageExtractor] = None) -> None:
        self.dataset_dir = dataset_dir
        self.manifest: List[EvidenceManifestEntry] = []
        self.manifest_by_id: Dict[str, EvidenceManifestEntry] = {}

        # Parsers registry
        self.parsers: List[BaseEvidenceParser] = [
            JSONEvidenceParser(),
            SQLEvidenceParser(),
            LogEvidenceParser(),
            TextEvidenceParser(),
            PDFEvidenceParser(),
            ImageEvidenceParser(extractor=image_extractor),
            CSVDatasetParser(),
        ]

        # In-memory indexes
        self._all_observations: List[EvidenceObservation] = []
        self._by_file_id: Dict[str, List[EvidenceObservation]] = defaultdict(list)
        self._by_resource_id: Dict[str, List[EvidenceObservation]] = defaultdict(list)
        self._by_system_id: Dict[str, List[EvidenceObservation]] = defaultdict(list)
        self._by_identifier: Dict[str, List[EvidenceObservation]] = defaultdict(list)

        # Operational activities index
        self.activities: List[SystemActivity] = []
        self._activities_by_resource: Dict[str, List[SystemActivity]] = defaultdict(list)

        self.warnings: List[IngestionWarning] = []
        self._is_loaded = False

    def load_manifest(self, manifest_path: Optional[str] = None) -> None:
        """Load and validate evidence_files.csv."""
        path = manifest_path or os.path.join(self.dataset_dir, "evidence_files.csv")
        if not os.path.exists(path):
            self.warnings.append(
                IngestionWarning(
                    file_id=None,
                    file_path=path,
                    warning_type="MANIFEST_NOT_FOUND",
                    message=f"Manifest file not found at {path}",
                )
            )
            return

        self.manifest = CSVDatasetParser.parse_evidence_manifest(path)
        self.manifest_by_id = {entry.file_id: entry for entry in self.manifest}

    def load_system_activity(self, activity_path: Optional[str] = None) -> None:
        """Load and index operational events from system_activity.csv."""
        path = activity_path or os.path.join(self.dataset_dir, "system_activity.csv")
        if not os.path.exists(path):
            return
        self.activities = CSVDatasetParser.parse_system_activities(path)
        self._activities_by_resource.clear()
        for act in self.activities:
            if act.resource_id:
                self._activities_by_resource[act.resource_id].append(act)

    def get_activities_for_resource(
        self,
        resource_id: str,
        cutoff: Optional[datetime] = None,
    ) -> List[SystemActivity]:
        """Query system activities for a given resource ID up to cutoff."""
        if not self.activities:
            self.load_system_activity()
        acts = self._activities_by_resource.get(resource_id, [])
        if cutoff is None:
            return list(acts)
        return [a for a in acts if a.event_time <= cutoff]

    def load_all_evidence(self, force_reload: bool = False) -> None:
        """Parse all evidence files from the manifest into memory once."""
        if self._is_loaded and not force_reload:
            return

        if not self.manifest:
            self.load_manifest()

        self._all_observations.clear()
        self._by_file_id.clear()
        self._by_resource_id.clear()
        self._by_system_id.clear()
        self._by_identifier.clear()
        self.warnings.clear()

        for entry in self.manifest:
            # Resolve real path relative to dataset_dir
            real_path = os.path.join(self.dataset_dir, entry.file_path)
            if not os.path.exists(real_path):
                # Try relative to repo root if path already includes dataset/
                if os.path.exists(entry.file_path):
                    real_path = entry.file_path
                else:
                    self.warnings.append(
                        IngestionWarning(
                            file_id=entry.file_id,
                            file_path=real_path,
                            warning_type="FILE_NOT_FOUND",
                            message=f"Evidence file missing on disk: {entry.file_path}",
                        )
                    )
                    continue

            # Find matching parser
            parser = self._get_parser_for_file(real_path)
            if not parser:
                self.warnings.append(
                    IngestionWarning(
                        file_id=entry.file_id,
                        file_path=real_path,
                        warning_type="UNSUPPORTED_FORMAT",
                        message=f"No parser available for {entry.file_path}",
                    )
                )
                continue

            # Parse file safely
            observations = parser.parse(real_path, manifest_entry=entry)
            for obs in observations:
                if obs.file_captured_at is None and entry.captured_at is not None:
                    obs.file_captured_at = entry.captured_at
                self._index_observation(obs)

        # Collect parser warnings
        for p in self.parsers:
            self.warnings.extend(p.warnings)

        self._is_loaded = True

    def _get_parser_for_file(self, file_path: str) -> Optional[BaseEvidenceParser]:
        for parser in self.parsers:
            if parser.can_parse(file_path):
                return parser
        return None

    def _index_observation(self, obs: EvidenceObservation) -> None:
        """Add observation to internal indexes."""
        self._all_observations.append(obs)
        if obs.evidence_id:
            self._by_file_id[obs.evidence_id].append(obs)
        if obs.resource_id:
            self._by_resource_id[obs.resource_id].append(obs)
        if obs.system_id:
            self._by_system_id[obs.system_id].append(obs)

        # Index all identifiers (case-insensitive for emails, verbatim for IDs)
        for _, val in obs.identifiers.items():
            if val:
                clean_val = val.strip().lower()
                self._by_identifier[clean_val].append(obs)

    def get_observations_for_user(
        self,
        user_graph: UserIdentityGraph,
        cutoff: Optional[datetime] = None,
    ) -> List[EvidenceObservation]:
        """Query observations matching any user identity alias on or before cutoff, deduplicated logically."""
        if not self._is_loaded:
            self.load_all_evidence()

        matched: List[EvidenceObservation] = []
        seen_logical_keys: Set[Tuple[str, str, str, str]] = set()

        # Collect all query terms
        query_terms: Set[str] = set()
        query_terms.add(user_graph.user_id.lower())
        for e in user_graph.emails:
            query_terms.add(e.lower())
        for p in user_graph.phones:
            query_terms.add(p.lower())
        for h in user_graph.email_hashes:
            query_terms.add(h.lower())
        for n in user_graph.names:
            query_terms.add(n.lower())

        for term in query_terms:
            for obs in self._by_identifier.get(term, []):
                # Logical deduplication prevents duplicate steps
                logical_key = (obs.system_id, obs.resource_id, obs.evidence_id, obs.extracted_state)
                if logical_key not in seen_logical_keys:
                    if cutoff is None or is_observation_temporally_valid(obs, cutoff):
                        seen_logical_keys.add(logical_key)
                        matched.append(obs)

        return matched

    def get_observations_for_resource(
        self,
        resource_id: str,
        cutoff: Optional[datetime] = None,
    ) -> List[EvidenceObservation]:
        """Query observations for a specific resource ID on or before cutoff."""
        if not self._is_loaded:
            self.load_all_evidence()

        res = self._by_resource_id.get(resource_id, [])
        if cutoff is None:
            return list(res)
        return [o for o in res if is_observation_temporally_valid(o, cutoff)]

    def get_observations_for_file(
        self,
        file_id: str,
        cutoff: Optional[datetime] = None,
    ) -> List[EvidenceObservation]:
        """Query observations from a specific evidence file on or before cutoff."""
        if not self._is_loaded:
            self.load_all_evidence()

        res = self._by_file_id.get(file_id, [])
        if cutoff is None:
            return list(res)
        return [o for o in res if is_observation_temporally_valid(o, cutoff)]

    def get_all_observations(
        self,
        cutoff: Optional[datetime] = None,
    ) -> List[EvidenceObservation]:
        """Retrieve all indexed observations, optionally bounded by cutoff."""
        if not self._is_loaded:
            self.load_all_evidence()

        if cutoff is None:
            return list(self._all_observations)
        return [o for o in self._all_observations if is_observation_temporally_valid(o, cutoff)]
