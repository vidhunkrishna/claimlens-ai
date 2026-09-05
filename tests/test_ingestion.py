import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.services.ingestion_service import (
    ingest_claim_from_directory,
    ingest_raw_claim_package
)
from src.models.evidence import DocumentType

client = TestClient(app)

def test_ingest_valid_claims_disk():
    """
    Test that all synthetic claims CLM-001 through CLM-005 ingest cleanly.
    """
    for claim_id in ["CLM-001", "CLM-002", "CLM-003", "CLM-004", "CLM-005"]:
        result = ingest_claim_from_directory(claim_id)
        assert result.status == "SUCCESS", f"Ingestion failed for valid claim {claim_id}: {result.errors}"
        assert result.package is not None
        assert result.package.claim_id == claim_id
        assert len(result.package.documents) >= 3
        assert len(result.package.facts) > 0
        
        # Verify fact provenance attributes
        for fact in result.package.facts:
            assert fact.claim_id == claim_id
            assert fact.document_id is not None
            assert fact.document_type in DocumentType
            assert fact.fact_name is not None
            assert fact.source_reference is not None

def test_missing_mandatory_document():
    """
    Test validation failure when a mandatory document (e.g. CLAIM_FORM) is missing.
    """
    raw_docs = [
        {
            "document_id": "DOC-TEST-RE",
            "claim_id": "CLM-TEST",
            "document_type": "REPAIR_ESTIMATE",
            "source": "Workshop",
            "content": "Estimate content",
            "metadata": {"amount": 5000}
        },
        {
            "document_id": "DOC-TEST-ID",
            "claim_id": "CLM-TEST",
            "document_type": "INCIDENT_DESCRIPTION",
            "source": "Claimant",
            "content": "Incident statement",
            "metadata": {}
        }
    ]
    result = ingest_raw_claim_package("CLM-TEST", raw_docs)
    assert result.status == "FAILED"
    error_codes = [err.error_code for err in result.errors]
    assert "MISSING_MANDATORY_DOCUMENT" in error_codes

def test_malformed_document():
    """
    Test validation failure when a document is missing required top-level schema fields.
    """
    raw_docs = [
        {
            "document_id": "DOC-TEST-CF",
            "claim_id": "CLM-TEST",
            "document_type": "CLAIM_FORM",
            "source": "", # Empty source
            "content": "Claim Form Content"
        }
    ]
    result = ingest_raw_claim_package("CLM-TEST", raw_docs)
    assert result.status == "FAILED"
    error_codes = [err.error_code for err in result.errors]
    assert "MISSING_REQUIRED_FIELDS" in error_codes

def test_wrong_claim_id():
    """
    Test validation failure when a document specifies a claim ID mismatch.
    """
    raw_docs = [
        {
            "document_id": "DOC-TEST-CF",
            "claim_id": "CLM-WRONG-999", # Mismatch!
            "document_type": "CLAIM_FORM",
            "source": "Claimant",
            "content": "Claim Form",
            "metadata": {}
        },
        {
            "document_id": "DOC-TEST-RE",
            "claim_id": "CLM-TEST",
            "document_type": "REPAIR_ESTIMATE",
            "source": "Workshop",
            "content": "Estimate",
            "metadata": {}
        },
        {
            "document_id": "DOC-TEST-ID",
            "claim_id": "CLM-TEST",
            "document_type": "INCIDENT_DESCRIPTION",
            "source": "Claimant",
            "content": "Statement",
            "metadata": {}
        }
    ]
    result = ingest_raw_claim_package("CLM-TEST", raw_docs)
    assert result.status == "FAILED"
    error_codes = [err.error_code for err in result.errors]
    assert "WRONG_CLAIM_ID" in error_codes

def test_duplicate_document():
    """
    Test validation failure when duplicate document IDs or duplicate CLAIM_FORMs exist.
    """
    raw_docs = [
        {
            "document_id": "DOC-DUP-CF",
            "claim_id": "CLM-TEST",
            "document_type": "CLAIM_FORM",
            "source": "Claimant",
            "content": "Claim Form 1",
            "metadata": {}
        },
        {
            "document_id": "DOC-DUP-CF", # Duplicate ID!
            "claim_id": "CLM-TEST",
            "document_type": "CLAIM_FORM",
            "source": "Claimant",
            "content": "Claim Form 2",
            "metadata": {}
        },
        {
            "document_id": "DOC-TEST-RE",
            "claim_id": "CLM-TEST",
            "document_type": "REPAIR_ESTIMATE",
            "source": "Workshop",
            "content": "Estimate",
            "metadata": {}
        },
        {
            "document_id": "DOC-TEST-ID",
            "claim_id": "CLM-TEST",
            "document_type": "INCIDENT_DESCRIPTION",
            "source": "Claimant",
            "content": "Statement",
            "metadata": {}
        }
    ]
    result = ingest_raw_claim_package("CLM-TEST", raw_docs)
    assert result.status == "FAILED"
    error_codes = [err.error_code for err in result.errors]
    assert "DUPLICATE_DOCUMENT_ID" in error_codes

def test_unsupported_document_type():
    """
    Test validation failure when an unsupported document_type is provided.
    """
    raw_docs = [
        {
            "document_id": "DOC-TEST-INVALID",
            "claim_id": "CLM-TEST",
            "document_type": "INVALID_DOC_TYPE_XYZ", # Unsupported!
            "source": "Unknown",
            "content": "Invalid content",
            "metadata": {}
        },
        {
            "document_id": "DOC-TEST-CF",
            "claim_id": "CLM-TEST",
            "document_type": "CLAIM_FORM",
            "source": "Claimant",
            "content": "Form",
            "metadata": {}
        },
        {
            "document_id": "DOC-TEST-RE",
            "claim_id": "CLM-TEST",
            "document_type": "REPAIR_ESTIMATE",
            "source": "Workshop",
            "content": "Estimate",
            "metadata": {}
        },
        {
            "document_id": "DOC-TEST-ID",
            "claim_id": "CLM-TEST",
            "document_type": "INCIDENT_DESCRIPTION",
            "source": "Claimant",
            "content": "Statement",
            "metadata": {}
        }
    ]
    result = ingest_raw_claim_package("CLM-TEST", raw_docs)
    assert result.status == "FAILED"
    error_codes = [err.error_code for err in result.errors]
    assert "UNSUPPORTED_DOCUMENT_TYPE" in error_codes

def test_api_ingest_endpoints():
    """
    Test FastAPI ingestion endpoints via TestClient.
    """
    # 1. GET /api/v1/ingest/claims
    res_list = client.get("/api/v1/ingest/claims")
    assert res_list.status_code == 200
    claims = res_list.json()
    assert "CLM-001" in claims

    # 2. POST /api/v1/ingest/CLM-001
    res_ingest = client.post("/api/v1/ingest/CLM-001")
    assert res_ingest.status_code == 200
    data = res_ingest.json()
    assert data["status"] == "SUCCESS"
    assert data["package"]["claim_id"] == "CLM-001"
    assert len(data["package"]["facts"]) > 0
