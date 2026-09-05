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
