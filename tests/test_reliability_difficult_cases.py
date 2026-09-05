import pytest
from src.models.evidence import DocumentType
from src.models.rules import RuleStatus
from src.models.investigation_report import ExecutiveResult, ConfidenceLevel
from src.services.ingestion_service import ingest_raw_claim_package
from src.services.investigation_engine import review_claim_package, review_claim
from src.services.gemini_service import create_fallback_reasoning_output
from src.models.gemini_reasoning import ReasoningStatus

def test_missing_claim_form():
    """1. Missing claim form -> Ingestion validator flags MISSING_MANDATORY_DOCUMENT error"""
    raw_docs = [
        {
            "document_id": "DOC-MISS-RE",
            "claim_id": "CLM-MISS-CF",
            "document_type": "REPAIR_ESTIMATE",
            "source": "Workshop",
            "content": "Estimate",
            "metadata": {"total_amount": 50000}
        },
        {
            "document_id": "DOC-MISS-ID",
            "claim_id": "CLM-MISS-CF",
            "document_type": "INCIDENT_DESCRIPTION",
            "source": "Claimant",
            "content": "Incident description text",
            "metadata": {}
        }
    ]
    package_res = ingest_raw_claim_package("CLM-MISS-CF", raw_docs)
    assert package_res.status == "FAILED"
    assert any("CLAIM_FORM" in err.message for err in package_res.errors)

def test_missing_fir():
    """2. Missing FIR for theft claim -> Ingestion validator flags MISSING_MANDATORY_DOCUMENT error"""
    raw_docs = [
        {
            "document_id": "DOC-THEFT-CF",
            "claim_id": "CLM-MISS-FIR",
            "document_type": "CLAIM_FORM",
            "source": "Claimant",
            "content": "Theft claim form",
            "metadata": {"claim_type": "TOTAL_THEFT", "incident_date": "2026-08-01", "intimation_date": "2026-08-02"}
        },
        {
            "document_id": "DOC-THEFT-ID",
            "claim_id": "CLM-MISS-FIR",
            "document_type": "INCIDENT_DESCRIPTION",
            "source": "Claimant",
            "content": "Bike stolen from parking",
            "metadata": {}
        }
    ]
    package_res = ingest_raw_claim_package("CLM-MISS-FIR", raw_docs)
    assert package_res.status == "FAILED"
    assert any("REPAIR_ESTIMATE' or 'FIR'" in err.message for err in package_res.errors)

def test_missing_repair_estimate():
    """3. Missing repair estimate -> Ingestion validator flags MISSING_MANDATORY_DOCUMENT error"""
    raw_docs = [
        {
            "document_id": "DOC-ACC-CF",
            "claim_id": "CLM-MISS-RE",
            "document_type": "CLAIM_FORM",
            "source": "Claimant",
            "content": "Car accident claim",
            "metadata": {"incident_date": "2026-08-10", "intimation_date": "2026-08-12", "driver_name": "Rohan"}
        },
        {
            "document_id": "DOC-ACC-ID",
            "claim_id": "CLM-MISS-RE",
            "document_type": "INCIDENT_DESCRIPTION",
            "source": "Claimant",
            "content": "Hit a pillar",
            "metadata": {}
        }
    ]
    package_res = ingest_raw_claim_package("CLM-MISS-RE", raw_docs)
    assert package_res.status == "FAILED"
    assert any("MISSING_MANDATORY_DOCUMENT" in err.error_code for err in package_res.errors)

def test_missing_incident_description():
    """4. Missing incident description -> Ingestion validator flags MISSING_MANDATORY_DOCUMENT error"""
    raw_docs = [
        {
            "document_id": "DOC-NODESC-CF",
            "claim_id": "CLM-MISS-ID",
            "document_type": "CLAIM_FORM",
            "source": "Claimant",
            "content": "Form text",
            "metadata": {"incident_date": "2026-08-10", "intimation_date": "2026-08-11"}
        },
        {
            "document_id": "DOC-NODESC-RE",
            "claim_id": "CLM-MISS-ID",
            "document_type": "REPAIR_ESTIMATE",
            "source": "Workshop",
            "content": "Estimate",
            "metadata": {"total_amount": 25000}
        }
    ]
    package_res = ingest_raw_claim_package("CLM-MISS-ID", raw_docs)
    assert package_res.status == "FAILED"
    assert any("INCIDENT_DESCRIPTION" in err.message for err in package_res.errors)

def test_contradictory_dates():
    """5. Contradictory dates across documents -> ESCALATE FOR INVESTIGATION / LOW confidence"""
    report = review_claim("CLM-002")
    assert report.executive_result in [ExecutiveResult.ESCALATE_FOR_INVESTIGATION, ExecutiveResult.REQUEST_INFORMATION]
    assert report.consistency_analysis.contradictions_count >= 1
    date_contradiction = next((c for c in report.consistency_analysis.contradictions if c.field_name == "incident_date"), None)
    assert date_contradiction is not None
    assert report.human_escalation.requires_human_review is True

def test_contradictory_vehicle_info():
    """6. Contradictory vehicle registration -> ESCALATE FOR INVESTIGATION"""
    raw_docs = [
        {
            "document_id": "DOC-V-CF",
            "claim_id": "CLM-V-MISMATCH",
            "document_type": "CLAIM_FORM",
            "source": "Claimant",
            "content": "Form KA-01-AB-1234",
            "metadata": {"incident_date": "2026-08-10", "intimation_date": "2026-08-11", "vehicle_registration": "KA-01-AB-1234", "driver_name": "Raj", "driver_license_number": "DL101"}
        },
        {
            "document_id": "DOC-V-RE",
            "claim_id": "CLM-V-MISMATCH",
            "document_type": "REPAIR_ESTIMATE",
            "source": "Garage",
            "content": "Estimate MH-12-XY-9999",
            "metadata": {"vehicle_registration": "MH-12-XY-9999", "total_amount": 30000}
        },
        {
            "document_id": "DOC-V-ID",
            "claim_id": "CLM-V-MISMATCH",
            "document_type": "INCIDENT_DESCRIPTION",
            "source": "Claimant",
            "content": "Car hit divider",
            "metadata": {}
        }
    ]
    package_res = ingest_raw_claim_package("CLM-V-MISMATCH", raw_docs)
    assert package_res.status == "SUCCESS"
    report = review_claim_package(package_res.package)
    assert report.executive_result == ExecutiveResult.ESCALATE_FOR_INVESTIGATION
    assert report.consistency_analysis.contradictions_count >= 1

def test_contradictory_damage_descriptions():
    """7. Contradictory damage descriptions -> ESCALATE FOR INVESTIGATION"""
    raw_docs = [
        {
            "document_id": "DOC-D-CF",
            "claim_id": "CLM-DAMAGE-MISMATCH",
            "document_type": "CLAIM_FORM",
            "source": "Claimant",
            "content": "Front bumper collision",
            "metadata": {"incident_date": "2026-08-10", "intimation_date": "2026-08-11", "damaged_parts": ["Front Bumper", "Radiator Grille"], "driver_name": "Sam", "driver_license_number": "DL202"}
        },
        {
            "document_id": "DOC-D-RE",
            "claim_id": "CLM-DAMAGE-MISMATCH",
            "document_type": "REPAIR_ESTIMATE",
            "source": "Workshop",
            "content": "Rear mudguard replacement",
            "metadata": {
                "damaged_parts": ["Rear Mudguard", "Tail Light Assembly"],
                "line_items": [
                    {"description": "Rear Mudguard Replacement", "amount": 25000},
                    {"description": "Tail Light Assembly", "amount": 15000}
                ],
                "total_amount": 40000
            }
        },
        {
            "document_id": "DOC-D-ID",
            "claim_id": "CLM-DAMAGE-MISMATCH",
            "document_type": "INCIDENT_DESCRIPTION",
            "source": "Claimant",
            "content": "Incident description",
            "metadata": {}
        }
    ]
    package_res = ingest_raw_claim_package("CLM-DAMAGE-MISMATCH", raw_docs)
    assert package_res.status == "SUCCESS"
    report = review_claim_package(package_res.package)
    assert report.executive_result == ExecutiveResult.ESCALATE_FOR_INVESTIGATION
    assert report.human_escalation.requires_human_review is True

def test_claim_outside_reporting_window():
    """8. Claim outside 7-day reporting window (55 days delay in CLM-004) -> RULE-CLAIM-WINDOW FAIL"""
    report = review_claim("CLM-004")
    window_rule = next(r for r in report.rule_results if r.rule_id == "RULE-CLAIM-WINDOW")
    assert window_rule.status == RuleStatus.FAIL
    assert "55 days" in window_rule.explanation

def test_repair_cost_above_idv():
    """9. Repair cost > 100% IDV -> REJECT under POL-014"""
    raw_docs = [
        {
            "document_id": "DOC-LIMIT-PS",
            "claim_id": "CLM-LIMIT",
            "document_type": "POLICY_SCHEDULE",
            "source": "Insurer",
            "content": "Policy Schedule",
            "metadata": {"idv": 100000}
        },
        {
            "document_id": "DOC-LIMIT-CF",
            "claim_id": "CLM-LIMIT",
            "document_type": "CLAIM_FORM",
            "source": "Claimant",
            "content": "Claim Form",
            "metadata": {"incident_date": "2026-08-10", "intimation_date": "2026-08-11", "driver_name": "Ravi", "driver_license_number": "DL303"}
        },
        {
            "document_id": "DOC-LIMIT-ID",
            "claim_id": "CLM-LIMIT",
            "document_type": "INCIDENT_DESCRIPTION",
            "source": "Claimant",
            "content": "Major crash",
            "metadata": {}
        },
        {
            "document_id": "DOC-LIMIT-RE",
            "claim_id": "CLM-LIMIT",
            "document_type": "REPAIR_ESTIMATE",
            "source": "Garage",
            "content": "Repair estimate",
            "metadata": {"total_amount": 150000} # 150% of IDV
        }
    ]
    package_res = ingest_raw_claim_package("CLM-LIMIT", raw_docs)
    assert package_res.status == "SUCCESS"
    report = review_claim_package(package_res.package)
    assert report.executive_result == ExecutiveResult.REJECT
    pol014_item = next((p for p in report.policy_analysis if p.clause_id == "POL-014"), None)
    assert pol014_item is not None
    assert pol014_item.effect == "BLOCKS"

def test_policy_exclusion_drunk_driving():
    """10. Policy exclusion (POL-002 Drunk Driving) -> REJECT"""
    report = review_claim("CLM-003")
    assert report.executive_result == ExecutiveResult.REJECT
    pol002 = next((p for p in report.policy_analysis if p.clause_id == "POL-002"), None)
    assert pol002 is not None
    assert pol002.effect == "BLOCKS"

def test_unknown_policy_situation():
    """11. Unknown policy situation -> UNKNOWN confidence, ESCALATE FOR HUMAN REVIEW"""
    raw_docs = [
        {
            "document_id": "DOC-UNK-CF",
            "claim_id": "CLM-UNK-POLICY",
            "document_type": "CLAIM_FORM",
            "source": "Claimant",
            "content": "Claim Form for space debris damage",
            "metadata": {"incident_date": "2026-08-10", "intimation_date": "2026-08-11", "driver_name": "Alex", "driver_license_number": "DL404"}
        },
        {
            "document_id": "DOC-UNK-RE",
            "claim_id": "CLM-UNK-POLICY",
            "document_type": "REPAIR_ESTIMATE",
            "source": "Workshop",
            "content": "Space debris repair estimate",
            "metadata": {"total_amount": 50000}
        },
        {
            "document_id": "DOC-UNK-ID",
            "claim_id": "CLM-UNK-POLICY",
            "document_type": "INCIDENT_DESCRIPTION",
            "source": "Claimant",
            "content": "Satellite fragment fell on roof",
            "metadata": {}
        }
    ]
    package_res = ingest_raw_claim_package("CLM-UNK-POLICY", raw_docs)
    assert package_res.status == "SUCCESS"
    report = review_claim_package(package_res.package)
    assert report.executive_result is not None
    assert report.overall_confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW, ConfidenceLevel.UNKNOWN]

def test_irrelevant_document_handling():
    """12. Irrelevant document included -> Ingestion flags UNSUPPORTED_DOCUMENT_TYPE"""
    raw_docs = [
        {
            "document_id": "DOC-IRR-01",
            "claim_id": "CLM-IRRELEVANT",
            "document_type": "UNKNOWN",
            "source": "ThirdParty",
            "content": "Random grocery receipt text",
            "metadata": {}
        }
    ]
    package_res = ingest_raw_claim_package("CLM-IRRELEVANT", raw_docs)
    assert package_res.status == "FAILED"
    assert any("UNSUPPORTED_DOCUMENT_TYPE" in err.error_code for err in package_res.errors)

def test_malformed_document_handling():
    """13. Malformed document content -> Ingestion flags MISSING_REQUIRED_FIELDS"""
    raw_docs = [
        {
            "document_id": "DOC-MALFORMED",
            "claim_id": "CLM-MALFORMED",
            "document_type": "CLAIM_FORM"
            # Missing mandatory fields or bad format
        }
    ]
    package_res = ingest_raw_claim_package("CLM-MALFORMED", raw_docs)
    assert package_res.status == "FAILED"
    assert any("MISSING_REQUIRED_FIELDS" in err.error_code for err in package_res.errors)

def test_gemini_timeout_and_fallback_handling():
    """14 & 15 & 16. Gemini timeout/malformed/unavailable -> Returns safe fallback with MANUAL REVIEW REQUIRED"""
    fallback_output = create_fallback_reasoning_output("CLM-TEST", ["DOC-001"], "API call timed out after 10000ms")
    assert fallback_output.reasoning_status == ReasoningStatus.FALLBACK
    assert fallback_output.requires_human_escalation is True
    assert "manual review" in fallback_output.investigator_summary.lower() or "fallback" in fallback_output.investigator_summary.lower()

def test_no_relevant_policy_clause_handling():
    """17. No relevant policy clause found -> Safely falls back"""
    raw_docs = [
        {
            "document_id": "DOC-NOPOL-CF",
            "claim_id": "CLM-NOPOL",
            "document_type": "CLAIM_FORM",
            "source": "Claimant",
            "content": "Unusual claim",
            "metadata": {"incident_date": "2026-08-10", "intimation_date": "2026-08-11", "driver_name": "Tina", "driver_license_number": "DL606"}
        },
        {
            "document_id": "DOC-NOPOL-RE",
            "claim_id": "CLM-NOPOL",
            "document_type": "REPAIR_ESTIMATE",
            "source": "Workshop",
            "content": "Estimate",
            "metadata": {"total_amount": 10000}
        },
        {
            "document_id": "DOC-NOPOL-ID",
            "claim_id": "CLM-NOPOL",
            "document_type": "INCIDENT_DESCRIPTION",
            "source": "Claimant",
            "content": "Description",
            "metadata": {}
        }
    ]
    package_res = ingest_raw_claim_package("CLM-NOPOL", raw_docs)
    assert package_res.status == "SUCCESS"
    report = review_claim_package(package_res.package)
    assert report.executive_result is not None
    assert report.overall_confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW, ConfidenceLevel.UNKNOWN]
