"""Unit tests for multi-format evidence parsers with synthetic fixtures."""

from datetime import datetime, timezone
import json
import os
import sqlite3
import tempfile
import pytest

from code.evidence.parsers.csv_parser import CSVDatasetParser
from code.evidence.parsers.image_parser import ImageEvidenceParser, ImageExtractor, MetadataImageExtractor
from code.evidence.parsers.json_parser import JSONEvidenceParser
from code.evidence.parsers.log_parser import LogEvidenceParser
from code.evidence.parsers.pdf_parser import PDFEvidenceParser
from code.evidence.parsers.sql_parser import SQLEvidenceParser
from code.evidence.parsers.txt_parser import TextEvidenceParser
from code.models import EvidenceManifestEntry, EvidenceObservation

try:
    import pymupdf  # type: ignore
except ImportError:
    pymupdf = None


@pytest.fixture
def manifest_stub():
    return EvidenceManifestEntry(
        file_id="ev_stub_01",
        file_path="evidence/synthetic_stub.dat",
        origin="test_source",
        captured_at=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
    )


# --- 1. CSV Parser Tests ---

def test_csv_parser_with_bom_and_provenance(manifest_stub):
    parser = CSVDatasetParser()
    csv_content = "\ufeffresource_id,system_id,email,state\nacc_1,account_service,user@example.com,PRESENT\n"

    with tempfile.NamedTemporaryFile("w", encoding="utf-8-sig", suffix=".csv", delete=False) as tf:
        tf.write(csv_content)
        temp_name = tf.name

    try:
        observations = parser.parse(temp_name, manifest_entry=manifest_stub)
        assert len(observations) == 1
        obs = observations[0]
        assert obs.resource_id == "acc_1"
        assert obs.system_id == "account_service"
        assert obs.extracted_state == "PRESENT"
        assert obs.evidence_id == manifest_stub.file_id
        assert obs.source_file == temp_name
        assert obs.extraction_method == "csv_row"
        assert obs.identifiers.get("email") == "user@example.com"
    finally:
        os.unlink(temp_name)


# --- 2. JSON & JSONL Parser Tests ---

def test_json_service_export_parser(manifest_stub):
    parser = JSONEvidenceParser()
    data = {
        "exported_at": "2026-09-01T12:00:00Z",
        "service_exports": {
            "account_service": {
                "profile_lookups": [
                    {"resource_id": "acc_101", "status_code": 404, "profile": None},
                    {"resource_id": "acc_102", "status_code": 200, "profile": {"email": "found@example.com"}},
                ]
            },
            "integration_service": {
                "connectors": [
                    {"resource_id": "flow_201", "enabled": True, "customer_email": "found@example.com"},
                    {"resource_id": "flow_202", "enabled": False, "customer_reference": "user_202"},
                ]
            },
            "backup_service": {
                "restore_entries": [
                    {"resource_id": "backup_301", "restore_allowed": False, "customer_email": "found@example.com"},
                ]
            },
        },
    }

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as tf:
        json.dump(data, tf)
        temp_name = tf.name

    try:
        observations = parser.parse(temp_name, manifest_entry=manifest_stub)
        assert len(observations) == 5

        by_res = {o.resource_id: o for o in observations}

        # 404 status maps to ABSENT
        assert by_res["acc_101"].extracted_state == "ABSENT"
        assert by_res["acc_101"].system_id == "account_service"

        # 200 status maps to PRESENT
        assert by_res["acc_102"].extracted_state == "PRESENT"
        assert by_res["acc_102"].identifiers["email"] == "found@example.com"

        # enabled=True maps to ACTIVE
        assert by_res["flow_201"].extracted_state == "ACTIVE"
        assert by_res["flow_201"].system_id == "integration_service"

        # enabled=False maps to DISABLED
        assert by_res["flow_202"].extracted_state == "DISABLED"

        # restore_allowed=False maps to BLOCKED
        assert by_res["backup_301"].extracted_state == "BLOCKED"
        assert by_res["backup_301"].system_id == "backup_service"
    finally:
        os.unlink(temp_name)


def test_jsonl_parser(manifest_stub):
    parser = JSONEvidenceParser()
    jsonl_content = (
        '{"resource_id": "rec_01", "system_id": "search_service", "email": "a@ex.com", "state": "PRESENT"}\n'
        '{"resource_id": "rec_02", "system_id": "search_service", "email": "b@ex.com", "state": "ABSENT"}\n'
    )

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as tf:
        tf.write(jsonl_content)
        temp_name = tf.name

    try:
        observations = parser.parse(temp_name, manifest_entry=manifest_stub)
        assert len(observations) == 2
        assert observations[0].resource_id == "rec_01"
        assert observations[0].extracted_state == "PRESENT"
        assert observations[1].resource_id == "rec_02"
        assert observations[1].extracted_state == "ABSENT"
    finally:
        os.unlink(temp_name)


def test_json_malformed_input(manifest_stub):
    parser = JSONEvidenceParser()
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as tf:
        tf.write("{malformed json line, broken syntax")
        temp_name = tf.name

    try:
        observations = parser.parse(temp_name, manifest_entry=manifest_stub)
        assert observations == []
        assert len(parser.warnings) > 0
        assert parser.warnings[0].warning_type == "JSON_PARSE_ERROR"
    finally:
        os.unlink(temp_name)


# --- 3. SQL Parser Tests ---

def test_sql_inventory_and_replica_parser(manifest_stub):
    parser = SQLEvidenceParser()
    sql_script = """
    BEGIN TRANSACTION;
    CREATE TABLE customer_profiles (
        resource_id TEXT PRIMARY KEY,
        customer_reference TEXT,
        full_name TEXT,
        email TEXT,
        phone TEXT,
        email_hash TEXT,
        account_status TEXT,
        updated_at TEXT
    );
    INSERT INTO customer_profiles VALUES ('acc_10', 'user_10', 'Test User', 'test@example.com', '+1234', 'hash1', 'ACTIVE', '2026-08-30T10:00:00Z');

    CREATE TABLE connector_subscriptions (
        resource_id TEXT PRIMARY KEY,
        customer_reference TEXT,
        customer_email TEXT,
        connector_name TEXT,
        enabled INTEGER,
        last_delivery_status TEXT,
        updated_at TEXT
    );
    INSERT INTO connector_subscriptions VALUES ('flow_10', 'user_10', 'test@example.com', 'test_sync', 1, 'delivered', '2026-08-30T10:00:00Z');

    CREATE TABLE backup_restore_entries (
        resource_id TEXT PRIMARY KEY,
        customer_reference TEXT,
        customer_email TEXT,
        archive_key TEXT,
        restore_allowed INTEGER,
        updated_at TEXT
    );
    INSERT INTO backup_restore_entries VALUES ('bak_10', 'user_10', 'test@example.com', 'key.tar', 0, '2026-08-30T10:00:00Z');
    COMMIT;
    """

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".sql", delete=False) as tf:
        tf.write(sql_script)
        temp_name = tf.name

    try:
        observations = parser.parse(temp_name, manifest_entry=manifest_stub)
        assert len(observations) == 3
        by_res = {o.resource_id: o for o in observations}

        assert by_res["acc_10"].system_id == "account_service"
        assert by_res["acc_10"].extracted_state == "PRESENT"
        assert by_res["acc_10"].identifiers["email"] == "test@example.com"

        assert by_res["flow_10"].system_id == "integration_service"
        assert by_res["flow_10"].extracted_state == "ACTIVE"

        assert by_res["bak_10"].system_id == "backup_service"
        assert by_res["bak_10"].extracted_state == "BLOCKED"
    finally:
        os.unlink(temp_name)


def test_sql_malformed_script(manifest_stub):
    parser = SQLEvidenceParser()
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".sql", delete=False) as tf:
        tf.write("CREATE TABLE broken syntax (;;; INVALID SQL")
        temp_name = tf.name

    try:
        observations = parser.parse(temp_name, manifest_entry=manifest_stub)
        assert observations == []
        assert len(parser.warnings) > 0
        assert parser.warnings[0].warning_type == "SQL_EXECUTION_ERROR"
    finally:
        os.unlink(temp_name)


# --- 4. Log Parser Tests ---

def test_log_trace_grouping_and_status(manifest_stub):
    parser = LogEvidenceParser()
    log_content = (
        '2026-09-01T10:00:00Z level=DEBUG service=support_replica trace_id=tr-100 event=query_started lookup_key=user@example.com\n'
        '2026-09-01T10:00:01Z level=INFO service=support_replica trace_id=tr-100 event=query_done resource_id=support_99 rows=1\n'
        '2026-09-01T10:05:00Z level=INFO service=account_service event=profile_lookup resource_id=acc_99 http_status=404 lookup_key=ghost@example.com\n'
    )

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".log", delete=False) as tf:
        tf.write(log_content)
        temp_name = tf.name

    try:
        observations = parser.parse(temp_name, manifest_entry=manifest_stub)
        assert len(observations) == 2
        by_res = {o.resource_id: o for o in observations}

        # Traced item should correlate lookup_key email with resource_id
        assert "support_99" in by_res
        s_obs = by_res["support_99"]
        assert s_obs.system_id == "support_platform"
        assert s_obs.extracted_state == "PRESENT"
        assert s_obs.identifiers.get("email") == "user@example.com"

        # Untraced 404 should map to ABSENT
        assert "acc_99" in by_res
        a_obs = by_res["acc_99"]
        assert a_obs.system_id == "account_service"
        assert a_obs.extracted_state == "ABSENT"
        assert a_obs.identifiers.get("email") == "ghost@example.com"
    finally:
        os.unlink(temp_name)


# --- 5. Plain Text Parser Tests ---

def test_txt_pipe_delimited_parser(manifest_stub):
    parser = TextEvidenceParser()
    txt_content = (
        "SHIFT HANDOVER\n"
        "- 2026-09-01T12:00:00Z | account_service | acc_01 | USER_PROFILE | NOT_FOUND | deleted@example.com\n"
        "- 2026-09-01T12:00:00Z | integration_service | flow_01 | DATA_FLOW | ACTIVE | user@example.com\n"
        "- 2026-09-01T12:00:00Z | backup_service | bak_01 | BACKUP_ARCHIVE | BLOCKED | user_50\n"
        "- 2026-09-01T12:00:00Z | analytics_platform | ana_01 | ANALYTICS_PROFILE | ANONYMIZED | no direct identifier\n"
    )

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as tf:
        tf.write(txt_content)
        temp_name = tf.name

    try:
        observations = parser.parse(temp_name, manifest_entry=manifest_stub)
        assert len(observations) == 4
        by_res = {o.resource_id: o for o in observations}

        assert by_res["acc_01"].extracted_state == "ABSENT"
        assert by_res["flow_01"].extracted_state == "ACTIVE"
        assert by_res["bak_01"].extracted_state == "BLOCKED"
        assert by_res["ana_01"].extracted_state == "ANONYMIZED"
    finally:
        os.unlink(temp_name)


# --- 6. PDF Parser Tests ---

def test_pdf_parser_with_pymupdf(manifest_stub):
    if pymupdf is None:
        pytest.skip("PyMuPDF not available")

    # Create synthetic PDF in memory
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text(
        pymupdf.Point(50, 50),
        "SUPPORT ATTACHMENT REPORT\nCustomer: priya@example.com\nUser ID: user_07\nSupport Ticket: support_001\n"
    )
    pdf_bytes = doc.tobytes()

    with tempfile.NamedTemporaryFile("wb", suffix=".pdf", delete=False) as tf:
        tf.write(pdf_bytes)
        temp_name = tf.name

    try:
        parser = PDFEvidenceParser()
        observations = parser.parse(temp_name, manifest_entry=manifest_stub)
        assert len(observations) >= 1
        obs = observations[0]
        assert obs.resource_id == "support_001"
        assert obs.identifiers.get("email") == "priya@example.com"
        assert obs.identifiers.get("user_id") == "user_07"
        assert obs.extracted_state == "PRESENT"
    finally:
        os.unlink(temp_name)


# --- 7. Image Parser Tests ---

def test_metadata_image_extractor(manifest_stub):
    parser = ImageEvidenceParser(extractor=MetadataImageExtractor())

    with tempfile.NamedTemporaryFile("wb", suffix=".png", delete=False) as tf:
        tf.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 50)
        temp_name = tf.name

    try:
        observations = parser.parse(temp_name, manifest_entry=manifest_stub)
        assert len(observations) == 1
        obs = observations[0]
        assert obs.extracted_state == "NOT_EXTRACTED"
        assert obs.raw_data.get("extraction_status") == "pending_vision"
        assert obs.extraction_method == "image_metadata_only"
    finally:
        os.unlink(temp_name)


def test_pluggable_custom_image_extractor(manifest_stub):
    class MockVisionExtractor(ImageExtractor):
        def extract(self, file_path, manifest_entry=None):
            return [
                EvidenceObservation(
                    source_file=file_path,
                    evidence_id=manifest_entry.file_id if manifest_entry else "",
                    timestamp=manifest_entry.captured_at if manifest_entry else None,
                    system_id="account_service",
                    resource_id="acc_vision_01",
                    data_category="SCREENSHOT",
                    extracted_state="PRESENT",
                    identifiers={"email": "vision_detected@example.com"},
                    extraction_method="mock_vision",
                )
            ]

    parser = ImageEvidenceParser(extractor=MockVisionExtractor())
    observations = parser.parse("dummy.png", manifest_entry=manifest_stub)
    assert len(observations) == 1
    assert observations[0].identifiers.get("email") == "vision_detected@example.com"
    assert observations[0].extraction_method == "mock_vision"
