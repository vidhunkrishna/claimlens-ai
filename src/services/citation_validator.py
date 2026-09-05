from typing import List, Set, Tuple
from src.models.gemini_reasoning import (
    GeminiReasoningOutput,
    ReasoningStatus,
    ReasoningAction
)

def validate_and_sanitize_citations(
    reasoning: GeminiReasoningOutput,
    valid_evidence_ids: List[str],
    valid_clause_ids: List[str]
) -> Tuple[GeminiReasoningOutput, List[str]]:
    """
    Validate Gemini citations against the set of valid evidence IDs (DOC-XXX) and policy clause IDs (POL-XXX)
    supplied in the prompt context. Sanitizes invalid citations and escalates if critical hallucinations occur.
    """
    evidence_set: Set[str] = set(valid_evidence_ids)
    clause_set: Set[str] = set(valid_clause_ids)
    warnings: List[str] = []

    # 1. Validate top-level cited evidence IDs
    sanitized_evidence_ids = []
    for doc_id in reasoning.cited_evidence_ids:
        if doc_id in evidence_set:
            sanitized_evidence_ids.append(doc_id)
        else:
            warnings.append(f"Sanitized unsupported evidence ID citation: '{doc_id}'")

    reasoning.cited_evidence_ids = sanitized_evidence_ids

    # 2. Validate top-level cited clause IDs
    sanitized_clause_ids = []
    for clause_id in reasoning.cited_policy_clause_ids:
        if clause_id in clause_set:
            sanitized_clause_ids.append(clause_id)
        else:
            warnings.append(f"Sanitized unsupported policy clause ID citation: '{clause_id}'")

    reasoning.cited_policy_clause_ids = sanitized_clause_ids

    # 3. Validate evidence IDs in semantic contradictions
    for contradiction in reasoning.semantic_contradictions:
        if contradiction.evidence_id_a not in evidence_set:
            warnings.append(f"Contradiction '{contradiction.finding_id}' referenced invalid evidence_id_a '{contradiction.evidence_id_a}'")
        if contradiction.evidence_id_b not in evidence_set:
            warnings.append(f"Contradiction '{contradiction.finding_id}' referenced invalid evidence_id_b '{contradiction.evidence_id_b}'")

    # 4. Validate clause IDs and evidence IDs in policy analysis
    for analysis in reasoning.policy_analysis:
        if analysis.clause_id not in clause_set:
            warnings.append(f"Policy analysis referenced invalid clause_id '{analysis.clause_id}'")
        
        valid_cites = [e for e in analysis.cited_evidence_ids if e in evidence_set]
        if len(valid_cites) != len(analysis.cited_evidence_ids):
            warnings.append(f"Policy analysis for '{analysis.clause_id}' contained invalid evidence citations")
        analysis.cited_evidence_ids = valid_cites

    # 5. If invalid citations occurred, flag as UNCERTAIN / ESCALATE
    if warnings:
        reasoning.reasoning_status = ReasoningStatus.UNCERTAIN
        reasoning.requires_human_escalation = True
        reasoning.recommended_action = ReasoningAction.ESCALATE
        esc_msg = f"Hallucinated or unsupported citations detected ({len(warnings)} issues). Escalated to human investigator."
        reasoning.escalation_reason = esc_msg

    return reasoning, warnings
