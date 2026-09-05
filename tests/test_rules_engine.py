import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.services.ingestion_service import ingest_claim_from_directory, ingest_raw_claim_package
from src.services.rules_engine import evaluate_deterministic_rules
from src.models.rules import RuleStatus, DeterministicRecommendation

client = TestClient(app)

def test_rule_eval_clm001_clean_case():
    """
    Test CLM-001 (Clean Normal Case) passes all rules and receives APPROVE recommendation.
    """
    ingest_res = ingest_claim_from_directory("CLM-001")
    assert ingest_res.status == "SUCCESS"
    
    report = evaluate_deterministic_rules(ingest_res.package)
    assert report.claim_id == "CLM-001"
    assert report.failed_count == 0
    assert report.overall_recommendation == DeterministicRecommendation.APPROVE
    
    # Check specific rule outcomes
    rules_map = {r.rule_id: r for r in report.rule_results}
    assert rules_map["RULE-DOC-COMPLETENESS"].status == RuleStatus.PASS
    assert rules_map["RULE-CLAIM-WINDOW"].status == RuleStatus.PASS
    assert rules_map["RULE-DRIVER-LICENSE"].status == RuleStatus.PASS
    assert rules_map["RULE-INTOXICATION-EXCLUSION"].status == RuleStatus.PASS
    assert rules_map["RULE-REPAIR-VS-IDV"].status == RuleStatus.PASS

def test_rule_eval_clm003_intoxication_exclusion():
    """
    Test CLM-003 fails RULE-INTOXICATION-EXCLUSION under clause POL-002 and receives REJECT.
    """
    ingest_res = ingest_claim_from_directory("CLM-003")
    assert ingest_res.status == "SUCCESS"
    
    report = evaluate_deterministic_rules(ingest_res.package)
    assert report.claim_id == "CLM-003"
    assert report.failed_count >= 1
    assert report.overall_recommendation == DeterministicRecommendation.REJECT
    
    rules_map = {r.rule_id: r for r in report.rule_results}
    intox_rule = rules_map["RULE-INTOXICATION-EXCLUSION"]
    assert intox_rule.status == RuleStatus.FAIL
    assert intox_rule.policy_clause_id == "POL-002"
    assert "0.12%" in intox_rule.explanation

def test_rule_eval_clm004_expired_window_and_missing_dl():
    """
    Test CLM-004 (55-day delay and missing DL) fails window and needs info for DL.
    """
    ingest_res = ingest_claim_from_directory("CLM-004")
    assert ingest_res.status == "SUCCESS"
    
    report = evaluate_deterministic_rules(ingest_res.package)
    assert report.claim_id == "CLM-004"
    assert report.overall_recommendation in [DeterministicRecommendation.REJECT, DeterministicRecommendation.REQUEST_INFORMATION]
    
    rules_map = {r.rule_id: r for r in report.rule_results}
    assert rules_map["RULE-CLAIM-WINDOW"].status == RuleStatus.FAIL
    assert rules_map["RULE-CLAIM-WINDOW"].policy_clause_id in ["POL-007", "POL-009"]
    assert rules_map["RULE-DRIVER-LICENSE"].status == RuleStatus.NEEDS_INFO

def test_repair_cost_above_idv_ctl_and_exceed_limit():
    """
    Test edge cases for repair cost vs IDV:
    1. > 75% of IDV triggers WARN (Constructive Total Loss POL-008).
    2. > 100% of IDV triggers FAIL (Exceeds Policy Limit POL-014).
    """
    # 1. >75% IDV CTL warning
    raw_ctl_docs = [
        {
            "document_id": "DOC-CTL-PS",
            "claim_id": "CLM-CTL",
            "document_type": "POLICY_SCHEDULE",
            "source": "Insurer",
            "content": "Policy",
            "metadata": {"idv": 100000}
        },
        {
            "document_id": "DOC-CTL-CF",
            "claim_id": "CLM-CTL",
            "document_type": "CLAIM_FORM",
            "source": "Claimant",
            "content": "Form",
            "metadata": {"incident_date": "2026-08-10", "intimation_date": "2026-08-11", "driver_name": "John", "driver_license_number": "DL123"}
        },
        {
            "document_id": "DOC-CTL-ID",
            "claim_id": "CLM-CTL",
            "document_type": "INCIDENT_DESCRIPTION",
            "source": "Claimant",
            "content": "Description",
            "metadata": {}
        },
        {
            "document_id": "DOC-CTL-RE",
            "claim_id": "CLM-CTL",
            "document_type": "REPAIR_ESTIMATE",
            "source": "Workshop",
            "content": "Estimate",
            "metadata": {"total_amount": 80000} # 80% of IDV
        }
    ]
    ingest_ctl = ingest_raw_claim_package("CLM-CTL", raw_ctl_docs)
    assert ingest_ctl.status == "SUCCESS"
    report_ctl = evaluate_deterministic_rules(ingest_ctl.package)
    rules_ctl = {r.rule_id: r for r in report_ctl.rule_results}
    assert rules_ctl["RULE-REPAIR-VS-IDV"].status == RuleStatus.WARN
    assert rules_ctl["RULE-REPAIR-VS-IDV"].policy_clause_id == "POL-008"

    # 2. >100% IDV Exceeds limit
    raw_exceed_docs = [
        dict(raw_ctl_docs[0], claim_id="CLM-EXCEED", document_id="DOC-EXCEED-PS", metadata={"idv": 100000}),
        dict(raw_ctl_docs[1], claim_id="CLM-EXCEED", document_id="DOC-EXCEED-CF"),
        dict(raw_ctl_docs[2], claim_id="CLM-EXCEED", document_id="DOC-EXCEED-ID"),
        dict(raw_ctl_docs[3], claim_id="CLM-EXCEED", document_id="DOC-EXCEED-RE", metadata={"total_amount": 120000}) # 120% of IDV
    ]
    ingest_exceed = ingest_raw_claim_package("CLM-EXCEED", raw_exceed_docs)
    assert ingest_exceed.status == "SUCCESS"
    report_exceed = evaluate_deterministic_rules(ingest_exceed.package)
    rules_exceed = {r.rule_id: r for r in report_exceed.rule_results}
    assert rules_exceed["RULE-REPAIR-VS-IDV"].status == RuleStatus.FAIL
    assert rules_exceed["RULE-REPAIR-VS-IDV"].policy_clause_id == "POL-014"

def test_clm005_theft_key_surrender():
    """
    Test CLM-005 theft claim key surrender passes under POL-012.
    """
    ingest_res = ingest_claim_from_directory("CLM-005")
    assert ingest_res.status == "SUCCESS"
    
    report = evaluate_deterministic_rules(ingest_res.package)
    rules_map = {r.rule_id: r for r in report.rule_results}
    assert rules_map["RULE-THEFT-KEY-SURRENDER"].status == RuleStatus.PASS
    assert rules_map["RULE-THEFT-KEY-SURRENDER"].policy_clause_id == "POL-012"

def test_api_rules_endpoint():
    """
    Test API rule evaluation endpoint POST /api/v1/rules/evaluate/CLM-001.
    """
    res = client.post("/api/v1/rules/evaluate/CLM-001")
    assert res.status_code == 200
    data = res.json()
    assert data["claim_id"] == "CLM-001"
    assert data["overall_recommendation"] == "APPROVE"
    assert data["total_rules_evaluated"] == 7
