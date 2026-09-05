from typing import Dict, List, Any, Optional
from src.models.evidence import NormalizedClaimPackage, DocumentType
from src.models.rules import RuleStatus, RulesEvaluationReport
from src.models.contradictions import ContradictionReport, ContradictionSeverity
from src.models.gemini_reasoning import GeminiReasoningOutput, ReasoningStatus
from src.models.investigation_report import (
    ExecutiveResult,
    ConfidenceLevel,
    ClaimOverview,
    DocumentCompletenessSummary,
    ConsistencyAnalysisSummary,
    PolicyAnalysisItem,
    EvidenceFinding,
    HumanEscalationDetail,
    ClaimInvestigationReport,
)
from src.services.ingestion_service import (
    ingest_claim_from_directory,
    ingest_raw_claim_package
)
from src.services.rules_engine import evaluate_deterministic_rules, _get_fact_value
from src.services.contradiction_detector import detect_cross_document_contradictions
from src.services.retrieval_service import retrieve_clauses_for_claim, get_clause_by_id
from src.services.gemini_service import analyze_claim_with_gemini

def _build_claim_overview(package: NormalizedClaimPackage) -> ClaimOverview:
    facts = package.facts
    reg_no = _get_fact_value(facts, "registration_number") or _get_fact_value(facts, "vehicle_registration") or "N/A"
    make_model = _get_fact_value(facts, "make_model") or "N/A"
    v_type = _get_fact_value(facts, "vehicle_type") or "Private Motor Vehicle"
    c_type = _get_fact_value(facts, "claim_type") or "Accidental Damage"
    inc_date = _get_fact_value(facts, "incident_date") or _get_fact_value(facts, "theft_date") or "N/A"
    int_date = _get_fact_value(facts, "intimation_date") or "N/A"
    insured = _get_fact_value(facts, "insured_name") or _get_fact_value(facts, "claimant_name") or "N/A"
    idv_val = float(_get_fact_value(facts, "idv") or 0.0)
    est_val = float(_get_fact_value(facts, "estimated_claim_amount") or _get_fact_value(facts, "total_amount") or 0.0)

    return ClaimOverview(
        claim_id=package.claim_id,
        vehicle_registration=str(reg_no),
        vehicle_make_model=str(make_model),
        vehicle_type=str(v_type),
        claim_type=str(c_type),
        incident_date=str(inc_date),
        intimation_date=str(int_date),
        insured_name=str(insured),
        idv=idv_val,
        estimated_amount=est_val
    )

def _build_doc_completeness(package: NormalizedClaimPackage) -> DocumentCompletenessSummary:
    doc_types = {d.document_type for d in package.documents}
    submitted = [
        {"document_id": d.document_id, "document_type": d.document_type.value, "source": d.source}
        for d in package.documents
    ]
    
    has_cf = DocumentType.CLAIM_FORM in doc_types
    has_evidence = (DocumentType.REPAIR_ESTIMATE in doc_types) or (DocumentType.FIR in doc_types)
    has_id = DocumentType.INCIDENT_DESCRIPTION in doc_types

    missing = []
    if not has_cf:
        missing.append("CLAIM_FORM")
    if not has_evidence:
        missing.append("REPAIR_ESTIMATE / FIR")
    if not has_id:
        missing.append("INCIDENT_DESCRIPTION")

    return DocumentCompletenessSummary(
        has_claim_form=has_cf,
        has_fir_or_estimate=has_evidence,
        has_incident_description=has_id,
        is_complete=len(missing) == 0,
        submitted_documents=submitted,
        missing_documents=missing
    )

def _calculate_confidence_model(
    doc_summary: DocumentCompletenessSummary,
    contradiction_report: ContradictionReport,
    rules_report: RulesEvaluationReport,
    gemini_res: GeminiReasoningOutput,
    policy_items: List[PolicyAnalysisItem]
) -> tuple[ConfidenceLevel, str]:
    """
    Calculate explicit evidence confidence model classification: HIGH, MEDIUM, LOW, or UNKNOWN.
    Explains the exact rationale for the assigned confidence category.
    """
    if gemini_res.reasoning_status == ReasoningStatus.FALLBACK and not doc_summary.is_complete:
        return ConfidenceLevel.UNKNOWN, "UNKNOWN / MANUAL REVIEW REQUIRED: Incomplete evidence package and AI reasoning service unavailable."

    if len(policy_items) == 0:
        return ConfidenceLevel.UNKNOWN, "UNKNOWN / HUMAN REVIEW REQUIRED: No relevant policy clause found or applicable to this claim scenario."

    if contradiction_report.total_contradictions_found > 0:
        return ConfidenceLevel.LOW, f"LOW CONFIDENCE: Detected {contradiction_report.total_contradictions_found} severe cross-document evidence contradictions."

    if not doc_summary.is_complete:
        return ConfidenceLevel.LOW, f"LOW CONFIDENCE: Missing mandatory documentation ({', '.join(doc_summary.missing_documents)})."

    has_warnings = any(r.status == RuleStatus.WARN for r in rules_report.rule_results)
    needs_info = any(r.status == RuleStatus.NEEDS_INFO for r in rules_report.rule_results)

    if has_warnings or needs_info:
        return ConfidenceLevel.MEDIUM, "MEDIUM CONFIDENCE: All mandatory documents present, but deterministic rules flagged threshold warnings or required minor clarification."

    if rules_report.failed_count > 0:
        return ConfidenceLevel.HIGH, f"HIGH CONFIDENCE: Clear deterministic rule failure ({rules_report.failed_count} rules failed, e.g. policy exclusion breach)."

    return ConfidenceLevel.HIGH, "HIGH CONFIDENCE: Complete documentation submitted, 0 evidence contradictions detected, and all deterministic rules passed."

def review_claim_package(package: NormalizedClaimPackage) -> ClaimInvestigationReport:
    """
    Run complete end-to-end claim investigation pipeline combining:
    - Evidence ingestion & normalization
    - Deterministic rules engine
    - Cross-document contradiction detector
    - RAG local policy clause retrieval
    - Gemini semantic reasoning
    - Structured report builder with exact source text quotations
    """
    # 1. Evaluate Deterministic Rules
    rules_report: RulesEvaluationReport = evaluate_deterministic_rules(package)

    # 2. Detect Cross-Document Contradictions
    contradiction_report: ContradictionReport = detect_cross_document_contradictions(package)

    # 3. Retrieve Relevant Policy Clauses (RAG)
    retrieval_res = retrieve_clauses_for_claim(package, top_k=5)

    # 4. Gemini Reasoning (if key present / fallback safe)
    gemini_res: GeminiReasoningOutput = analyze_claim_with_gemini(package)

    # 5. Build Policy Analysis Items with Exact Stored Text
    policy_analysis_items: List[PolicyAnalysisItem] = []
    processed_clauses = set()

    # Include clauses from rules and retrieval
    retrieved_clause_ids = [c.clause_id for c in retrieval_res.retrieved_clauses]
    rule_clause_ids = [r.policy_clause_id for r in rules_report.rule_results if r.policy_clause_id]

    all_clause_ids = list(dict.fromkeys(rule_clause_ids + retrieved_clause_ids))

    for cid in all_clause_ids:
        if cid in processed_clauses:
            continue
        processed_clauses.add(cid)

        clause_obj = get_clause_by_id(cid)
        if not clause_obj:
            continue

        # Determine effect
        failing_rule = next((r for r in rules_report.rule_results if r.policy_clause_id == cid and r.status == RuleStatus.FAIL), None)
        if failing_rule:
            effect = "BLOCKS"
            explanation = failing_rule.explanation
        else:
            effect = "SUPPORTS"
            explanation = f"Clause '{clause_obj.title}' applies and supports claim coverage conditions."

        cites = [d.document_id for d in package.documents]

        policy_analysis_items.append(PolicyAnalysisItem(
            clause_id=clause_obj.clause_id,
            title=clause_obj.title,
            exact_clause_text=clause_obj.exact_text,
            effect=effect,
            explanation=explanation,
            cited_evidence_ids=cites[:3]
        ))

    # 6. Calculate Confidence Model
    doc_summary = _build_doc_completeness(package)
    confidence_lvl, confidence_exp = _calculate_confidence_model(
        doc_summary, contradiction_report, rules_report, gemini_res, policy_analysis_items
    )

    # 7. Synthesize Decision Matrix
    # Check for Policy Exclusion REJECTION
    rule_rejections = [r for r in rules_report.rule_results if r.status == RuleStatus.FAIL]
    is_rejected = len(rule_rejections) > 0 and any(r.policy_clause_id in ["POL-002", "POL-003", "POL-014"] for r in rule_rejections)

    has_missing_mandatory_docs = not doc_summary.is_complete
    needs_info_rules = [r for r in rules_report.rule_results if r.status == RuleStatus.NEEDS_INFO]
    has_severe_contradictions = contradiction_report.total_contradictions_found > 0 or gemini_res.reasoning_status == ReasoningStatus.CONTRADICTION_DETECTED

    if is_rejected:
        exec_result = ExecutiveResult.REJECT
    elif has_severe_contradictions:
        exec_result = ExecutiveResult.ESCALATE_FOR_INVESTIGATION
    elif has_missing_mandatory_docs or len(needs_info_rules) > 0:
        exec_result = ExecutiveResult.REQUEST_INFORMATION
    elif len(policy_analysis_items) == 0:
        exec_result = ExecutiveResult.ESCALATE_FOR_INVESTIGATION
    else:
        exec_result = ExecutiveResult.APPROVE

    # 8. Build Itemized Evidence Findings with Exact Source Excerpts
    findings: List[EvidenceFinding] = []
    finding_counter = 1

    # Add Contradiction Findings
    for c in contradiction_report.contradictions:
        doc_a = next((d for d in package.documents if d.document_id == c.source_document_a_id), None)
        excerpt_a = f"{c.field_name} = '{c.source_value_a}' in {doc_a.source if doc_a else c.source_document_a_id}"

        findings.append(EvidenceFinding(
            finding_id=f"FINDING-{package.claim_id}-{finding_counter:03d}",
            title=f"Cross-Document Contradiction: {c.field_name.replace('_', ' ').title()}",
            severity=c.severity.value,
            explanation=c.explanation,
            source_document_id=c.source_document_a_id,
            source_document_type=c.source_document_a_type,
            exact_source_text=excerpt_a,
            policy_clause_id="POL-009",
            confidence=ConfidenceLevel.LOW
        ))
        finding_counter += 1

    # Add Rule Failure / Warning / Needs Info Findings
    for r in rules_report.rule_results:
        if r.status != RuleStatus.PASS:
            src_id = r.source_document_ids[0] if r.source_document_ids else "PACKAGE"
            doc_obj = next((d for d in package.documents if d.document_id == src_id), None)
            exact_text = doc_obj.content[:150] if doc_obj else r.explanation

            findings.append(EvidenceFinding(
                finding_id=f"FINDING-{package.claim_id}-{finding_counter:03d}",
                title=f"Rule Result: {r.rule_name} [{r.status.value}]",
                severity="HIGH" if r.status == RuleStatus.FAIL else "MEDIUM",
                explanation=r.explanation,
                source_document_id=src_id,
                source_document_type=doc_obj.document_type.value if doc_obj else "RULE_ENGINE",
                exact_source_text=exact_text,
                policy_clause_id=r.policy_clause_id,
                confidence=ConfidenceLevel.HIGH if r.status == RuleStatus.FAIL else ConfidenceLevel.MEDIUM
            ))
            finding_counter += 1

    # 9. Recommendation Rationale
    if exec_result == ExecutiveResult.APPROVE:
        rationale = f"Claim '{package.claim_id}' meets all policy coverage requirements. Evidence is fully consistent, mandatory documents are present, and all deterministic rules pass."
    elif exec_result == ExecutiveResult.REJECT:
        rejection_reasons = [r.explanation for r in rules_report.rule_results if r.status == RuleStatus.FAIL]
        rationale = f"Claim '{package.claim_id}' is REJECTED due to explicit policy conditions / exclusions breach: {'; '.join(rejection_reasons)}"
    elif exec_result == ExecutiveResult.REQUEST_INFORMATION:
        req_reasons = [f"Missing {d}" for d in doc_summary.missing_documents] + [r.explanation for r in needs_info_rules]
        rationale = f"Claim '{package.claim_id}' requires additional information before final adjudication: {'; '.join(req_reasons)}"
    else:
        escalate_reasons = [c.explanation for c in contradiction_report.contradictions]
        if not escalate_reasons and len(policy_analysis_items) == 0:
            escalate_reasons = ["UNKNOWN / HUMAN REVIEW: No relevant policy clause found or matched."]
        rationale = f"Claim '{package.claim_id}' is ESCALATED FOR HUMAN INVESTIGATION due to cross-document evidence contradictions or unknown policy applicability: {'; '.join(escalate_reasons)}"

    # 10. Human Escalation Rationale & Points
    requires_escalation = exec_result in [ExecutiveResult.ESCALATE_FOR_INVESTIGATION, ExecutiveResult.REQUEST_INFORMATION]
    escalation_points = []
    for c in contradiction_report.contradictions:
        escalation_points.append(f"Contradiction in {c.field_name}: '{c.source_value_a}' ({c.source_document_a_id}) vs '{c.source_value_b}' ({c.source_document_b_id})")
    for r in needs_info_rules:
        escalation_points.append(f"Policy requirement check '{r.rule_name}': {r.explanation}")
    if gemini_res.reasoning_status == ReasoningStatus.FALLBACK:
        escalation_points.append(f"MANUAL REVIEW REQUIRED: Gemini reasoning service fallback triggered ({gemini_res.escalation_reason})")
    if len(policy_analysis_items) == 0:
        escalation_points.append("UNKNOWN / HUMAN REVIEW: No applicable policy clause identified.")

    human_escalation = HumanEscalationDetail(
        requires_human_review=requires_escalation,
        reason="Human investigator review required due to evidence contradictions, missing mandatory documentation, or AI service fallback." if requires_escalation else "No human escalation required. Automated review verified clean evidence.",
        escalation_points=escalation_points
    )

    return ClaimInvestigationReport(
        executive_result=exec_result,
        overall_confidence=confidence_lvl,
        confidence_explanation=confidence_exp,
        claim_overview=_build_claim_overview(package),
        document_completeness=doc_summary,
        consistency_analysis=ConsistencyAnalysisSummary(
            consistent_facts_count=len(package.facts) - (contradiction_report.total_contradictions_found * 2),
            contradictions_count=contradiction_report.total_contradictions_found,
            contradictions=contradiction_report.contradictions
        ),
        policy_analysis=policy_analysis_items,
        rule_results=rules_report.rule_results,
        evidence_findings=findings,
        recommendation_rationale=rationale,
        human_escalation=human_escalation
    )

def review_claim(claim_id: str) -> ClaimInvestigationReport:
    """
    Review a claim ID from disk through the complete 9-section investigation pipeline.
    """
    ingest_res = ingest_claim_from_directory(claim_id)
    if ingest_res.status == "FAILED" or not ingest_res.package:
        raise Exception(f"Claim ingestion failed for ID '{claim_id}': {[e.message for e in ingest_res.errors]}")
    return review_claim_package(ingest_res.package)
