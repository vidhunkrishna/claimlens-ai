from datetime import datetime
from typing import Dict, List, Any, Optional
from src.models.evidence import NormalizedClaimPackage, DocumentType, Fact
from src.models.rules import (
    RuleStatus,
    RuleResult,
    DeterministicRecommendation,
    RulesEvaluationReport,
)
from src.services.dataset_loader import load_policy

def _get_fact_value(facts: List[Fact], fact_name: str) -> Optional[Any]:
    """Helper to retrieve first matching fact value by name."""
    for f in facts:
        if f.fact_name == fact_name and f.value is not None:
            return f.value
    return None

def _get_fact(facts: List[Fact], fact_name: str) -> Optional[Fact]:
    """Helper to retrieve first matching Fact object by name."""
    for f in facts:
        if f.fact_name == fact_name and f.value is not None:
            return f
    return None

def parse_date(date_str: Any) -> Optional[datetime]:
    """Helper to parse standard YYYY-MM-DD date strings."""
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d")
    except ValueError:
        return None

def evaluate_doc_completeness(package: NormalizedClaimPackage) -> RuleResult:
    """
    Check mandatory document submission rules (POL-010).
    """
    doc_types = {doc.document_type for doc in package.documents}
    doc_ids = [doc.document_id for doc in package.documents]

    has_claim_form = DocumentType.CLAIM_FORM in doc_types
    has_incident_desc = DocumentType.INCIDENT_DESCRIPTION in doc_types
    has_estimate_or_fir = (DocumentType.REPAIR_ESTIMATE in doc_types) or (DocumentType.FIR in doc_types)

    missing = []
    if not has_claim_form:
        missing.append("CLAIM_FORM")
    if not has_incident_desc:
        missing.append("INCIDENT_DESCRIPTION")
    if not has_estimate_or_fir:
        missing.append("REPAIR_ESTIMATE or FIR")

    if missing:
        return RuleResult(
            rule_id="RULE-DOC-COMPLETENESS",
            policy_clause_id="POL-010",
            rule_name="Mandatory Document Submission Checklist",
            status=RuleStatus.NEEDS_INFO,
            explanation=f"Missing mandatory documents: {', '.join(missing)}. Claim requires complete evidence packet.",
            input_values={"submitted_types": [dt.value for dt in doc_types], "missing_types": missing},
            source_document_ids=doc_ids
        )

    return RuleResult(
        rule_id="RULE-DOC-COMPLETENESS",
        policy_clause_id="POL-010",
        rule_name="Mandatory Document Submission Checklist",
        status=RuleStatus.PASS,
        explanation="All mandatory document types (Claim Form, Evidence, Incident Statement) are present.",
        input_values={"submitted_types": [dt.value for dt in doc_types]},
        source_document_ids=doc_ids
    )

def evaluate_claim_window(package: NormalizedClaimPackage) -> RuleResult:
    """
    Check claim intimation and reporting windows (POL-007, POL-009).
    """
    facts = package.facts
    doc_ids = [f.document_id for f in facts if f.fact_name in ["incident_date", "theft_date", "intimation_date"]]

    incident_date_val = _get_fact_value(facts, "incident_date") or _get_fact_value(facts, "theft_date")
    intimation_date_val = _get_fact_value(facts, "intimation_date")

    inc_dt = parse_date(incident_date_val)
    int_dt = parse_date(intimation_date_val)

    if not inc_dt or not int_dt:
        return RuleResult(
            rule_id="RULE-CLAIM-WINDOW",
            policy_clause_id="POL-009",
            rule_name="Claim Reporting Window Check",
            status=RuleStatus.NEEDS_INFO,
            explanation="Unable to verify reporting window: missing valid incident_date or intimation_date.",
            input_values={"incident_date": incident_date_val, "intimation_date": intimation_date_val},
            source_document_ids=list(set(doc_ids))
        )

    delay_days = (int_dt - inc_dt).days
    
    # Check if theft claim
    claim_type = _get_fact_value(facts, "claim_type")
    is_theft = (claim_type == "TOTAL_THEFT") or (DocumentType.KEY_DECLARATION in {d.document_type for d in package.documents})

    max_allowed = 2 if is_theft else 7

    if delay_days < 0:
        return RuleResult(
            rule_id="RULE-CLAIM-WINDOW",
            policy_clause_id="POL-009",
            rule_name="Claim Reporting Window Check",
            status=RuleStatus.FAIL,
            explanation=f"Invalid dates: Intimation date ({intimation_date_val}) predates incident date ({incident_date_val}).",
            input_values={"incident_date": incident_date_val, "intimation_date": intimation_date_val, "delay_days": delay_days},
            source_document_ids=list(set(doc_ids))
        )

    if delay_days > max_allowed:
        return RuleResult(
            rule_id="RULE-CLAIM-WINDOW",
            policy_clause_id="POL-007",
            rule_name="Claim Reporting Window Check",
            status=RuleStatus.FAIL,
            explanation=f"Claim reported {delay_days} days after incident. Exceeds mandatory {max_allowed}-day reporting window under clause POL-007 & POL-009.",
            input_values={"incident_date": incident_date_val, "intimation_date": intimation_date_val, "delay_days": delay_days, "max_allowed_days": max_allowed},
            source_document_ids=list(set(doc_ids))
        )

    return RuleResult(
        rule_id="RULE-CLAIM-WINDOW",
        policy_clause_id="POL-009",
        rule_name="Claim Reporting Window Check",
        status=RuleStatus.PASS,
        explanation=f"Claim intimatted within {delay_days} days of incident (within the {max_allowed}-day policy window).",
        input_values={"incident_date": incident_date_val, "intimation_date": intimation_date_val, "delay_days": delay_days},
        source_document_ids=list(set(doc_ids))
    )

def evaluate_driver_license(package: NormalizedClaimPackage) -> RuleResult:
    """
    Check driver license availability and validity (POL-003, POL-010).
    """
    facts = package.facts
    dl_no_fact = _get_fact(facts, "driver_license_number")
    dl_provided = _get_fact_value(facts, "driver_license_provided")
    driver_name = _get_fact_value(facts, "driver_name")
    
    doc_ids = [dl_no_fact.document_id] if dl_no_fact else []

    dl_no = dl_no_fact.value if dl_no_fact else None

    if not dl_no or str(dl_no).strip() == "" or dl_provided is False:
        return RuleResult(
            rule_id="RULE-DRIVER-LICENSE",
            policy_clause_id="POL-010",
            rule_name="Valid Driving License Verification",
            status=RuleStatus.NEEDS_INFO,
            explanation="Driver license number or document is missing from claim submission. Clause POL-010 requires valid DL copy.",
            input_values={"driver_name": driver_name, "driver_license_number": dl_no},
            source_document_ids=doc_ids
        )

    # Expiry check if available
    dl_expiry_val = _get_fact_value(facts, "driver_license_expiry")
    inc_date_val = _get_fact_value(facts, "incident_date")
    
    exp_dt = parse_date(dl_expiry_val)
    inc_dt = parse_date(inc_date_val)

    if exp_dt and inc_dt and exp_dt < inc_dt:
        return RuleResult(
            rule_id="RULE-DRIVER-LICENSE",
            policy_clause_id="POL-003",
            rule_name="Valid Driving License Verification",
            status=RuleStatus.FAIL,
            explanation=f"Driving license expired on {dl_expiry_val}, prior to incident date ({inc_date_val}). Clause POL-003 excludes liability.",
            input_values={"driver_license_number": dl_no, "expiry_date": dl_expiry_val, "incident_date": inc_date_val},
            source_document_ids=doc_ids
        )

    return RuleResult(
        rule_id="RULE-DRIVER-LICENSE",
        policy_clause_id="POL-003",
        rule_name="Valid Driving License Verification",
        status=RuleStatus.PASS,
        explanation=f"Valid driver license provided ({dl_no}) for driver '{driver_name}'.",
        input_values={"driver_name": driver_name, "driver_license_number": dl_no},
        source_document_ids=doc_ids
    )

def evaluate_intoxication_exclusion(package: NormalizedClaimPackage) -> RuleResult:
    """
    Check drunk driving and substance abuse exclusion (POL-002).
    """
    facts = package.facts
    intox_confirmed = _get_fact_value(facts, "intoxication_confirmed")
    bac_level = _get_fact_value(facts, "blood_alcohol_concentration_bac")
    sec_charged = _get_fact_value(facts, "sections_charged") or []

    fir_doc = next((d for d in package.documents if d.document_type == DocumentType.FIR), None)
    doc_ids = [fir_doc.document_id] if fir_doc else []

    is_intoxicated = (intox_confirmed is True) or ("Sec 185 Motor Vehicles Act" in sec_charged) or ("Section 185 Motor Vehicles Act" in sec_charged)

    if is_intoxicated:
        return RuleResult(
            rule_id="RULE-INTOXICATION-EXCLUSION",
            policy_clause_id="POL-002",
            rule_name="Intoxication & Substance Abuse Exclusion Check",
            status=RuleStatus.FAIL,
            explanation=f"Claim excludes liability under clause POL-002: Driver was intoxicated at accident time (BAC: {bac_level}, Charges: {sec_charged}).",
            input_values={"intoxication_confirmed": intox_confirmed, "bac_level": bac_level, "sections_charged": sec_charged},
            source_document_ids=doc_ids
        )

    return RuleResult(
        rule_id="RULE-INTOXICATION-EXCLUSION",
        policy_clause_id="POL-002",
        rule_name="Intoxication & Substance Abuse Exclusion Check",
        status=RuleStatus.PASS,
        explanation="No evidence of driver intoxication or alcohol breach detected.",
        input_values={"intoxication_confirmed": False},
        source_document_ids=doc_ids
    )

def evaluate_repair_vs_idv(package: NormalizedClaimPackage) -> RuleResult:
    """
    Check repair cost against Insured Declared Value (IDV) (POL-008, POL-014).
    """
    facts = package.facts
    idv_val = _get_fact_value(facts, "idv")
    est_amount_val = _get_fact_value(facts, "total_amount") or _get_fact_value(facts, "estimated_claim_amount")

    ps_doc = next((d for d in package.documents if d.document_type == DocumentType.POLICY_SCHEDULE), None)
    re_doc = next((d for d in package.documents if d.document_type == DocumentType.REPAIR_ESTIMATE), None)
    
    doc_ids = [d.document_id for d in [ps_doc, re_doc] if d is not None]

    if idv_val is None or est_amount_val is None:
        return RuleResult(
            rule_id="RULE-REPAIR-VS-IDV",
            policy_clause_id="POL-008",
            rule_name="Repair Cost vs. IDV Threshold Check",
            status=RuleStatus.NEEDS_INFO,
            explanation="Missing IDV or repair estimate amount for valuation check.",
            input_values={"idv": idv_val, "estimated_amount": est_amount_val},
            source_document_ids=doc_ids
        )

    idv = float(idv_val)
    est = float(est_amount_val)

    if est > idv:
        return RuleResult(
            rule_id="RULE-REPAIR-VS-IDV",
            policy_clause_id="POL-014",
            rule_name="Repair Cost vs. IDV Threshold Check",
            status=RuleStatus.FAIL,
            explanation=f"Estimated repair cost (₹{est:,.2f}) exceeds total vehicle IDV (₹{idv:,.2f}). Exceeds policy liability limit under clause POL-014.",
            input_values={"idv": idv, "estimated_amount": est, "ratio": round(est/idv, 2)},
            source_document_ids=doc_ids
        )

    if est > (0.75 * idv):
        return RuleResult(
            rule_id="RULE-REPAIR-VS-IDV",
            policy_clause_id="POL-008",
            rule_name="Repair Cost vs. IDV Threshold Check",
            status=RuleStatus.WARN,
            explanation=f"Estimated repair cost (₹{est:,.2f}) exceeds 75% of IDV (₹{idv:,.2f}). Triggers Constructive Total Loss (CTL) under clause POL-008.",
            input_values={"idv": idv, "estimated_amount": est, "ctl_threshold_75_pct": 0.75 * idv, "ratio": round(est/idv, 2)},
            source_document_ids=doc_ids
        )

    return RuleResult(
        rule_id="RULE-REPAIR-VS-IDV",
        policy_clause_id="POL-008",
        rule_name="Repair Cost vs. IDV Threshold Check",
        status=RuleStatus.PASS,
        explanation=f"Estimated repair cost (₹{est:,.2f}) is within vehicle IDV (₹{idv:,.2f}) ({round((est/idv)*100, 1)}% of IDV).",
        input_values={"idv": idv, "estimated_amount": est, "ratio_pct": round((est/idv)*100, 1)},
        source_document_ids=doc_ids
    )

def evaluate_deductible_calculation(package: NormalizedClaimPackage) -> RuleResult:
    """
    Calculate compulsory deductible and admissible net claim amount (POL-013).
    """
    facts = package.facts
    v_type = _get_fact_value(facts, "vehicle_type") or "Private Car"
    engine_cc = _get_fact_value(facts, "engine_capacity_cc") or 1197
    est_amount = _get_fact_value(facts, "total_amount") or _get_fact_value(facts, "estimated_claim_amount") or 0

    if "Two-Wheeler" in str(v_type):
        compulsory_deductible = 100
    elif engine_cc > 1500:
        compulsory_deductible = 2000
    else:
        compulsory_deductible = 1000

    net_admissible = max(0.0, float(est_amount) - compulsory_deductible)

    return RuleResult(
        rule_id="RULE-DEDUCTIBLE-CALCULATION",
        policy_clause_id="POL-013",
        rule_name="Compulsory Deductible Calculation",
        status=RuleStatus.PASS,
        explanation=f"Compulsory deductible of ₹{compulsory_deductible} applied under clause POL-013 for {v_type}. Net admissible amount: ₹{net_admissible:,.2f}.",
        input_values={
            "vehicle_type": v_type,
            "engine_cc": engine_cc,
            "gross_claim_amount": est_amount,
            "compulsory_deductible": compulsory_deductible,
            "net_admissible_amount": net_admissible
        },
        source_document_ids=[d.document_id for d in package.documents]
    )

def evaluate_theft_key_surrender(package: NormalizedClaimPackage) -> RuleResult:
    """
    Check theft claim key surrender compliance (POL-012).
    """
    facts = package.facts
    claim_type = _get_fact_value(facts, "claim_type")
    is_theft = (claim_type == "TOTAL_THEFT") or (DocumentType.KEY_DECLARATION in {d.document_type for d in package.documents})

    if not is_theft:
        return RuleResult(
            rule_id="RULE-THEFT-KEY-SURRENDER",
            policy_clause_id="POL-012",
            rule_name="Theft Key Surrender Compliance",
            status=RuleStatus.PASS,
            explanation="Not a theft claim; key surrender rule is not applicable.",
            input_values={"is_theft_claim": False},
            source_document_ids=[]
        )

    keys_surrendered = _get_fact_value(facts, "keys_surrendered") or _get_fact_value(facts, "keys_surrendered_count")
    kd_doc = next((d for d in package.documents if d.document_type == DocumentType.KEY_DECLARATION), None)
    doc_ids = [kd_doc.document_id] if kd_doc else []

    if keys_surrendered is None:
        return RuleResult(
            rule_id="RULE-THEFT-KEY-SURRENDER",
            policy_clause_id="POL-012",
            rule_name="Theft Key Surrender Compliance",
            status=RuleStatus.NEEDS_INFO,
            explanation="Theft claim requires key surrender verification under clause POL-012. Key declaration document missing.",
            input_values={"keys_surrendered": None},
            source_document_ids=doc_ids
        )

    if int(keys_surrendered) < 2:
        return RuleResult(
            rule_id="RULE-THEFT-KEY-SURRENDER",
            policy_clause_id="POL-012",
            rule_name="Theft Key Surrender Compliance",
            status=RuleStatus.FAIL,
            explanation=f"Only {keys_surrendered} key(s) surrendered. Clause POL-012 requires both original manufacturer keys to prevent negligence repudiation.",
            input_values={"keys_surrendered": keys_surrendered, "required": 2},
            source_document_ids=doc_ids
        )

    return RuleResult(
        rule_id="RULE-THEFT-KEY-SURRENDER",
        policy_clause_id="POL-012",
        rule_name="Theft Key Surrender Compliance",
        status=RuleStatus.PASS,
        explanation=f"Both original manufacturer ignition keys ({keys_surrendered} keys) surrendered and verified.",
        input_values={"keys_surrendered": keys_surrendered},
        source_document_ids=doc_ids
    )

def evaluate_deterministic_rules(package: NormalizedClaimPackage, policy_data: Optional[Dict[str, Any]] = None) -> RulesEvaluationReport:
    """
    Run all deterministic insurance rules against a normalized claim package.
    """
    results: List[RuleResult] = [
        evaluate_doc_completeness(package),
        evaluate_claim_window(package),
        evaluate_driver_license(package),
        evaluate_intoxication_exclusion(package),
        evaluate_repair_vs_idv(package),
        evaluate_deductible_calculation(package),
        evaluate_theft_key_surrender(package),
    ]

    passed = len([r for r in results if r.status == RuleStatus.PASS])
    failed = len([r for r in results if r.status == RuleStatus.FAIL])
    warn = len([r for r in results if r.status == RuleStatus.WARN])
    needs_info = len([r for r in results if r.status == RuleStatus.NEEDS_INFO])

    # Determine overall deterministic recommendation
    if failed > 0:
        recommendation = DeterministicRecommendation.REJECT
    elif needs_info > 0:
        recommendation = DeterministicRecommendation.REQUEST_INFORMATION
    elif warn > 0:
        recommendation = DeterministicRecommendation.ESCALATE
    else:
        recommendation = DeterministicRecommendation.APPROVE

    return RulesEvaluationReport(
        claim_id=package.claim_id,
        total_rules_evaluated=len(results),
        passed_count=passed,
        failed_count=failed,
        warn_count=warn,
        needs_info_count=needs_info,
        overall_recommendation=recommendation,
        rule_results=results
    )
