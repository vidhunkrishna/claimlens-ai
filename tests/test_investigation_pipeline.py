import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.services.investigation_engine import review_claim
from src.models.investigation_report import ExecutiveResult

client = TestClient(app)

def test_pipeline_clm001_approve():
    """
    Test CLM-001 (Clean Normal Case) -> APPROVE
    """
    report = review_claim("CLM-001")
    assert report.executive_result == ExecutiveResult.APPROVE
    assert report.claim_overview.claim_id == "CLM-001"
    assert report.document_completeness.is_complete is True
    assert report.consistency_analysis.contradictions_count == 0
    assert report.human_escalation.requires_human_review is False
    assert "meets all policy coverage requirements" in report.recommendation_rationale

def test_pipeline_clm002_escalate_contradiction():
    """
    Test CLM-002 (Contradiction Case) -> ESCALATE FOR INVESTIGATION / REQUEST INFORMATION
    """
    report = review_claim("CLM-002")
    assert report.executive_result in [ExecutiveResult.ESCALATE_FOR_INVESTIGATION, ExecutiveResult.REQUEST_INFORMATION]
    assert report.consistency_analysis.contradictions_count >= 4
    assert report.human_escalation.requires_human_review is True
    assert len(report.evidence_findings) >= 4
    assert len(report.human_escalation.escalation_points) >= 4

def test_pipeline_clm003_reject_drunk_driving():
    """
    Test CLM-003 (Drunk Driving Exclusion) -> REJECT
    """
    report = review_claim("CLM-003")
    assert report.executive_result == ExecutiveResult.REJECT
    assert report.claim_overview.claim_id == "CLM-003"
    
    # Verify policy analysis contains POL-002 with BLOCKS effect and exact stored text
    pol002 = next((p for p in report.policy_analysis if p.clause_id == "POL-002"), None)
    assert pol002 is not None
    assert pol002.effect == "BLOCKS"
    assert "Blood Alcohol Concentration" in pol002.exact_clause_text

def test_pipeline_clm004_request_information_missing_dl():
    """
    Test CLM-004 (Missing DL & 55-day delay) -> REQUEST INFORMATION
    """
    report = review_claim("CLM-004")
    assert report.executive_result == ExecutiveResult.REQUEST_INFORMATION
    assert report.human_escalation.requires_human_review is True
    assert "missing" in report.recommendation_rationale.lower() or "delay" in report.recommendation_rationale.lower()

def test_pipeline_clm005_approve_theft():
    """
    Test CLM-005 (Total Theft with FIR & Key Surrender) -> APPROVE
    """
    report = review_claim("CLM-005")
    assert report.executive_result == ExecutiveResult.APPROVE
    assert report.claim_overview.claim_type == "TOTAL_THEFT"
    assert report.document_completeness.is_complete is True
    assert report.consistency_analysis.contradictions_count == 0
    assert report.human_escalation.requires_human_review is False

def test_api_investigation_endpoint():
    """
    Test API endpoint POST /api/v1/investigation/review/CLM-001 returns 200 OK with full 9-section report.
    """
    res = client.post("/api/v1/investigation/review/CLM-001")
    assert res.status_code == 200
    data = res.json()
    assert data["executive_result"] == "APPROVE"
    assert data["claim_overview"]["claim_id"] == "CLM-001"
    assert "policy_analysis" in data
    assert "evidence_findings" in data
    assert "human_escalation" in data

def test_api_investigation_review_package_endpoint():
    """
    Test API endpoint POST /api/v1/investigation/review/package processes custom document packages cleanly.
    Verifies that 'package' is not misinterpreted as a claim_id and returns a complete 9-section report.
    """
    import json
    from pathlib import Path
    
    fixtures_dir = Path("data/upload_fixtures/CLM-001")
    docs = []
    if fixtures_dir.exists():
        for p in fixtures_dir.glob("*.json"):
            with open(p, "r", encoding="utf-8") as f:
                docs.append(json.load(f))
    else:
        # Fallback inline test fixture if directory missing
        docs = [
            {
                "document_id": "DOC-CLM001-CF",
                "claim_id": "CLM-001",
                "document_type": "CLAIM_FORM",
                "source": "Claimant",
                "content": {"incident_date": "2026-03-10", "policy_number": "POL-1001", "loss_amount": 45000.0}
            },
            {
                "document_id": "DOC-CLM001-RE",
                "claim_id": "CLM-001",
                "document_type": "REPAIR_ESTIMATE",
                "source": "Garage",
                "content": {"estimated_cost": 45000.0}
            },
            {
                "document_id": "DOC-CLM001-ID",
                "claim_id": "CLM-001",
                "document_type": "INCIDENT_DESCRIPTION",
                "source": "Claimant",
                "content": {"description": "Vehicle scraped against pillar"}
            }
        ]

    # Test payload where claim_id is "package" (e.g. from URL endpoint name matching)
    payload = {"claim_id": "package", "documents": docs}
    res = client.post("/api/v1/investigation/review/package", json=payload)
    assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["claim_overview"]["claim_id"] == "CLM-001"
    assert "executive_result" in data
    assert "policy_analysis" in data
    assert "evidence_findings" in data
    assert "human_escalation" in data

def test_clm004_custom_package_review_endpoint():
    """
    Regression test for CLM-004 custom package upload (claim_form, estimate, incident_description).
    Verifies that POST /api/v1/investigation/review/package with payload claim_id='package' or 'CLM-004'
    processes correctly and returns 200 OK with REQUEST INFORMATION status.
    """
    import json
    from pathlib import Path

    clm004_dir = Path("data/upload_fixtures/CLM-004")
    docs = []
    for filename in ["claim_form.json", "estimate.json", "incident_description.json"]:
        p = clm004_dir / filename
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                docs.append(json.load(f))

    assert len(docs) == 3

    payload = {"claim_id": "package", "documents": docs}
    res = client.post("/api/v1/investigation/review/package", json=payload)
    assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["claim_overview"]["claim_id"] == "CLM-004"
    assert data["executive_result"] == "REQUEST INFORMATION"
    assert data["document_completeness"]["is_complete"] is True
    assert data["human_escalation"]["requires_human_review"] is True
