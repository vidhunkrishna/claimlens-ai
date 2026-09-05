import pytest
from src.services.dataset_loader import (
    load_policy,
    load_claim,
    list_all_claims,
    validate_dataset_integrity
)

def test_policy_structure():
    """
    Validate motor_policy.json structure and clause completeness.
    """
    policy = load_policy()
    assert "policy_metadata" in policy
    assert "clauses" in policy
    
    clauses = policy["clauses"]
    assert len(clauses) >= 14
    
    clause_ids = [c["clause_id"] for c in clauses]
    expected_clauses = [f"POL-{i:03d}" for i in range(1, 15)]
    for expected in expected_clauses:
        assert expected in clause_ids, f"Missing clause {expected} in policy"

def test_claims_list():
    """
    Validate that all 5 required claims exist in data/claims.
    """
    claims = list_all_claims()
    expected_claims = ["CLM-001", "CLM-002", "CLM-003", "CLM-004", "CLM-005"]
    for expected in expected_claims:
        assert expected in claims, f"Missing expected claim directory {expected}"

def test_document_schema_and_metadata():
    """
    Validate every claim document has required schema fields:
    document_id, claim_id, document_type, source, content, metadata.
    """
    claims = list_all_claims()
    for claim_id in claims:
        claim_package = load_claim(claim_id)
        docs = claim_package["documents"]
        assert len(docs) >= 3, f"Claim {claim_id} has insufficient documents"
        
        for doc_name, doc_content in docs.items():
            assert "document_id" in doc_content, f"Missing document_id in {claim_id}/{doc_name}"
            assert doc_content["claim_id"] == claim_id, f"Mismatched claim_id in {claim_id}/{doc_name}"
            assert "document_type" in doc_content, f"Missing document_type in {claim_id}/{doc_name}"
            assert "source" in doc_content, f"Missing source in {claim_id}/{doc_name}"
            assert "content" in doc_content, f"Missing content in {claim_id}/{doc_name}"
            assert "metadata" in doc_content, f"Missing metadata in {claim_id}/{doc_name}"

def test_clm001_clean_case():
    """
    Validate CLM-001 (Clean Normal Case) attributes.
    """
    claim = load_claim("CLM-001")["documents"]
    cf = claim["claim_form"]["metadata"]
    re = claim["repair_estimate"]["metadata"]
    
    assert cf["incident_date"] == "2026-08-10"
    assert cf["estimated_claim_amount"] == 18500
    assert re["total_amount"] == 18500
    assert cf["driver_name"] == "Rajesh Kumar"

def test_clm002_contradiction_case():
    """
    Validate CLM-002 (Contradiction Case) deliberate conflicts.
    """
    claim = load_claim("CLM-002")["documents"]
    cf = claim["claim_form"]["metadata"]
    id_doc = claim["incident_description"]["metadata"]
    re = claim["repair_estimate"]["metadata"]
    
    # Date contradiction (15th vs 18th)
    assert cf["incident_date"] != id_doc["incident_date_mentioned"]
    
    # Driver contradiction (Suresh vs Priya)
    assert cf["driver_name"] != id_doc["driver_name_mentioned"]
    
    # Repair estimate pre-dates incident
    assert re["estimate_date"] < cf["incident_date"]

def test_clm003_policy_block_case():
    """
    Validate CLM-003 (Drunk Driving Block) contains BAC breach of POL-002.
    """
    claim = load_claim("CLM-003")["documents"]
    fir = claim["fir"]["metadata"]
    
    assert fir["intoxication_confirmed"] is True
    assert fir["violates_policy_clause"] == "POL-002"
    assert "Sec 185 Motor Vehicles Act" in fir["sections_charged"]

def test_clm004_missing_information_case():
    """
    Validate CLM-004 (Missing Info Case) has null DL and intimation delay.
    """
    claim = load_claim("CLM-004")["documents"]
    cf = claim["claim_form"]["metadata"]
    
    assert cf["driver_license_number"] is None
    assert cf["driver_license_provided"] is False
    assert cf["intimation_delay_days"] > 7

def test_clm005_theft_case():
    """
    Validate CLM-005 (Theft Case) has FIR and surrender of both original keys.
    """
    claim = load_claim("CLM-005")["documents"]
    fir = claim["fir"]["metadata"]
    kd = claim["key_declaration"]["metadata"]
    
    assert fir["section_charged"] == "Section 379 IPC"
    assert kd["keys_surrendered"] == 2
    assert kd["all_keys_accounted_for"] is True

def test_dataset_loader_integrity():
    """
    Validate overall dataset loader output.
    """
    report = validate_dataset_integrity()
    assert report["total_claims"] == 5
    assert report["policy_clauses_count"] == 14
    for claim_id, claim_rep in report["claim_reports"].items():
        assert claim_rep["has_mandatory_documents"] is True
