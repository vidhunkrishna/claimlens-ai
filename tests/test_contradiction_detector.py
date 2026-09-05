import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.services.ingestion_service import (
    ingest_claim_from_directory,
    ingest_raw_claim_package
)
from src.services.contradiction_detector import (
    detect_cross_document_contradictions,
    _are_values_equivalent
)
from src.models.contradictions import ContradictionSeverity, ContradictionStatus

client = TestClient(app)

def test_clm001_no_contradiction():
    """
    Test CLM-001 (Clean Normal Case) returns 0 contradictions.
    """
    ingest_res = ingest_claim_from_directory("CLM-001")
    assert ingest_res.status == "SUCCESS"
    
    report = detect_cross_document_contradictions(ingest_res.package)
    assert report.claim_id == "CLM-001"
    assert report.total_contradictions_found == 0
    assert report.requires_investigator_review is False

def test_clm002_multiple_contradictions_detected():
    """
    Test CLM-002 (Contradiction Case) detects all 4+ deliberate cross-document contradictions.
    """
    ingest_res = ingest_claim_from_directory("CLM-002")
    assert ingest_res.status == "SUCCESS"

    report = detect_cross_document_contradictions(ingest_res.package)
    assert report.claim_id == "CLM-002"
    assert report.total_contradictions_found >= 4
    assert report.high_severity_count >= 3
    assert report.requires_investigator_review is True

    fields_detected = {c.field_name for c in report.contradictions}
    assert "incident_date" in fields_detected
    assert "driver_name" in fields_detected
    assert "incident_location" in fields_detected
    assert "damaged_parts" in fields_detected or "estimate_date" in fields_detected

    # Verify provenance format
    for c in report.contradictions:
        assert c.source_document_a_id is not None
        assert c.source_document_b_id is not None
        assert c.source_value_a is not None
        assert c.source_value_b is not None
        assert c.status == ContradictionStatus.REQUIRES_INVESTIGATION

def test_equivalent_values_no_false_positive():
    """
    Test that equivalent values (e.g. 'Hyundai i20' vs 'Hyundai i20 Magna 1.2') do not trigger contradictions.
    """
    assert _are_values_equivalent("Hyundai i20", "Hyundai i20 Magna 1.2", "make_model") is True
    assert _are_values_equivalent("Green Acres Apartment, Bengaluru", "Basement Parking, Green Acres Apartment, Bengaluru", "incident_location") is True
    assert _are_values_equivalent("2026-08-10", "2026-08-10", "incident_date") is True

    # Raw package test with equivalent model/location
    raw_docs = [
        {
            "document_id": "DOC-EQ-CF",
            "claim_id": "CLM-EQ",
            "document_type": "CLAIM_FORM",
            "source": "Claimant",
            "content": "Content",
            "metadata": {
                "incident_date": "2026-08-10",
                "driver_name": "Rajesh Kumar",
                "incident_location": "Basement Parking, Green Acres Apartment, Bengaluru",
                "make_model": "Hyundai i20"
            }
        },
        {
            "document_id": "DOC-EQ-ID",
            "claim_id": "CLM-EQ",
            "document_type": "INCIDENT_DESCRIPTION",
            "source": "Claimant",
            "content": "Content",
            "metadata": {
                "incident_date_mentioned": "2026-08-10",
                "driver_name_mentioned": "Rajesh Kumar",
                "location_mentioned": "Green Acres Apartment, Bengaluru"
            }
        },
        {
            "document_id": "DOC-EQ-RE",
            "claim_id": "CLM-EQ",
            "document_type": "REPAIR_ESTIMATE",
            "source": "Workshop",
            "content": "Content",
            "metadata": {"estimate_date": "2026-08-11", "total_amount": 10000}
        }
    ]
    ingest_res = ingest_raw_claim_package("CLM-EQ", raw_docs)
    assert ingest_res.status == "SUCCESS"
    report = detect_cross_document_contradictions(ingest_res.package)
    assert report.total_contradictions_found == 0

def test_missing_value_graceful_handling():
    """
    Test missing fields in one document do NOT create false contradictions.
    """
    raw_docs = [
        {
            "document_id": "DOC-MIS-CF",
            "claim_id": "CLM-MIS",
            "document_type": "CLAIM_FORM",
            "source": "Claimant",
            "content": "Content",
            "metadata": {
                "incident_date": "2026-08-10",
                "driver_name": "John Doe",
                "incident_location": None # Missing location!
            }
        },
        {
            "document_id": "DOC-MIS-ID",
            "claim_id": "CLM-MIS",
            "document_type": "INCIDENT_DESCRIPTION",
            "source": "Claimant",
            "content": "Content",
            "metadata": {
                "incident_date_mentioned": "2026-08-10",
                "location_mentioned": "MG Road, Bengaluru"
            }
        },
        {
            "document_id": "DOC-MIS-RE",
            "claim_id": "CLM-MIS",
            "document_type": "REPAIR_ESTIMATE",
            "source": "Workshop",
            "content": "Content",
            "metadata": {"estimate_date": "2026-08-11"}
        }
    ]
    ingest_res = ingest_raw_claim_package("CLM-MIS", raw_docs)
    report = detect_cross_document_contradictions(ingest_res.package)
    assert report.total_contradictions_found == 0

def test_semantic_damage_description_mismatch():
    """
    Test front damage vs rear damage contradiction detection.
    """
    assert _are_values_equivalent(["Front Bumper", "Headlight"], ["Rear Mudguard", "Tail Light"], "damaged_parts") is False

def test_api_contradiction_endpoints():
    """
    Test FastAPI contradiction detection endpoint POST /api/v1/contradictions/detect/CLM-002.
    """
    res = client.post("/api/v1/contradictions/detect/CLM-002")
    assert res.status_code == 200
    data = res.json()
    assert data["claim_id"] == "CLM-002"
    assert data["total_contradictions_found"] >= 4
    assert data["requires_investigator_review"] is True
