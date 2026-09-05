import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from src.core.config import settings
from src.models.evidence import NormalizedClaimPackage
from src.models.gemini_reasoning import (
    GeminiReasoningOutput,
    ReasoningStatus,
    ReasoningAction,
)
from src.services.citation_validator import validate_and_sanitize_citations
from src.services.dataset_loader import load_policy

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_INSTRUCTIONS = """
You are ClaimLens AI, an expert, objective motor-insurance claims evidence-review assistant.
Your job is to analyze the provided evidence documents and policy clauses for a specific claim.

CRITICAL OPERATING RULES:
1. STRICT EVIDENCE-ONLY REASONING: You must NEVER invent or hallucinate documents, policy clauses, transaction values, dates, names, or quotes.
2. CITATION REQUIREMENT: You may cite ONLY evidence IDs (e.g., DOC-CLM001-CF) and policy clause IDs (e.g., POL-002) that are explicitly provided in the input prompt.
3. NO FALSE FRAUD ALLEGATIONS: Never declare fraud or accuse parties of criminal intent. Simply identify factual evidence contradictions or non-compliance.
4. SURFACE CONTRADICTIONS: Do not hide contradictions. If dates, times, locations, drivers, or damaged parts conflict across documents, explicitly report them.
5. MANDATORY ESCALATION ON UNCERTAINTY: If evidence is ambiguous, incomplete, contradictory, or insufficient to reach a decisive conclusion, set reasoning_status to "UNCERTAIN" or "CONTRADICTION_DETECTED", set requires_human_escalation to true, and set recommended_action to "REQUEST_INFORMATION" or "ESCALATE".
6. JSON OUTPUT ONLY: Return strict valid JSON adhering to the required schema.
"""

def create_fallback_reasoning_output(
    claim_id: str,
    valid_evidence_ids: List[str],
    reason: str = "Gemini reasoning service unavailable or returned invalid output. Escalated for manual review."
) -> GeminiReasoningOutput:
    """
    Construct a graceful, safe manual-review fallback response when Gemini API is unconfigured,
    times out, throws an exception, or returns unparseable content.
    """
    return GeminiReasoningOutput(
        reasoning_status=ReasoningStatus.FALLBACK,
        investigator_summary=f"Automated AI reasoning fallback triggered for Claim '{claim_id}': {reason}. The case has been safely routed for human investigator review.",
        semantic_contradictions=[],
        policy_analysis=[],
        recommended_action=ReasoningAction.ESCALATE,
        requires_human_escalation=True,
        escalation_reason=reason,
        cited_evidence_ids=valid_evidence_ids,
        cited_policy_clause_ids=[]
    )

def _build_evidence_context(package: NormalizedClaimPackage, policy_data: Optional[Dict[str, Any]] = None) -> Tuple[str, List[str], List[str]]:
    """
    Format claim package documents and policy clauses into structured text for LLM prompt.
    Returns (context_text, valid_evidence_ids, valid_clause_ids).
    """
    valid_evidence_ids = [doc.document_id for doc in package.documents]
    
    if not policy_data:
        policy_data = load_policy()

    clauses = policy_data.get("clauses", [])
    valid_clause_ids = [c["clause_id"] for c in clauses]

    lines = []
    lines.append(f"CLAIM ID: {package.claim_id}")
    lines.append("\n=== SUBMITTED EVIDENCE DOCUMENTS ===")
    
    for doc in package.documents:
        lines.append(f"\nDOCUMENT ID: {doc.document_id}")
        lines.append(f"DOCUMENT TYPE: {doc.document_type.value}")
        lines.append(f"SOURCE: {doc.source}")
        lines.append(f"CONTENT: {doc.content}")
        lines.append(f"METADATA: {json.dumps(doc.metadata, indent=2)}")

    lines.append("\n=== APPLICABLE MASTER POLICY CLAUSES ===")
    for c in clauses:
        lines.append(f"CLAUSE ID: {c['clause_id']} | TITLE: {c['title']}")
        lines.append(f"TEXT: {c['text']}")

    return "\n".join(lines), valid_evidence_ids, valid_clause_ids

def analyze_claim_with_gemini(
    package: NormalizedClaimPackage,
    policy_data: Optional[Dict[str, Any]] = None,
    api_key_override: Optional[str] = None
) -> GeminiReasoningOutput:
    """
    Perform semantic evidence reasoning using Gemini AI API.
    Fails gracefully to fallback state if key is missing, network times out, or output is invalid.
    """
    valid_evidence_ids = [doc.document_id for doc in package.documents]
    
    # 1. Check API Key
    api_key = api_key_override if api_key_override is not None else (os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY)
    if not api_key or api_key.strip() == "":
        logger.warning("GEMINI_API_KEY is not configured. Returning graceful fallback state.")
        return create_fallback_reasoning_output(
            claim_id=package.claim_id,
            valid_evidence_ids=valid_evidence_ids,
            reason="GEMINI_API_KEY is missing or unconfigured."
        )

    # 2. Build Prompt Context
    evidence_text, valid_ev_ids, valid_pol_ids = _build_evidence_context(package, policy_data)

    prompt = f"""{SYSTEM_PROMPT_INSTRUCTIONS}

EVIDENCE & POLICY CONTEXT:
{evidence_text}

JSON RESPONSE FORMAT REQUIREMENT:
Return a JSON object with EXACTLY the following keys:
{{
  "reasoning_status": "CONFIDENT" | "UNCERTAIN" | "CONTRADICTION_DETECTED",
  "investigator_summary": "Summary string citing DOC-XXX and POL-XXX IDs",
  "semantic_contradictions": [
    {{
      "finding_id": "CONT-001",
      "title": "Short title",
      "description": "Explanation",
      "evidence_id_a": "DOC-XXX",
      "evidence_id_b": "DOC-YYY",
      "severity": "HIGH" | "MEDIUM" | "LOW"
    }}
  ],
  "policy_analysis": [
    {{
      "clause_id": "POL-XXX",
      "relevance": "Why relevant",
      "effect": "SUPPORTS" | "BLOCKS" | "NEUTRAL",
      "explanation": "Detailed rationale",
      "cited_evidence_ids": ["DOC-XXX"]
    }}
  ],
  "recommended_action": "APPROVE" | "REJECT" | "REQUEST_INFORMATION" | "ESCALATE",
  "requires_human_escalation": true | false,
  "escalation_reason": "Reason string if escalation required else null",
  "cited_evidence_ids": ["DOC-XXX"],
  "cited_policy_clause_ids": ["POL-XXX"]
}}
"""

    try:
        # Import SDK dynamically
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key.strip())
        
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
        )

        if not response or not response.text:
            return create_fallback_reasoning_output(
                claim_id=package.claim_id,
                valid_evidence_ids=valid_ev_ids,
                reason="Gemini API returned an empty response."
            )

        raw_json_text = response.text.strip()
        
        # Clean markdown codeblocks if returned
        if raw_json_text.startswith("```json"):
            raw_json_text = raw_json_text[7:]
        if raw_json_text.startswith("```"):
            raw_json_text = raw_json_text[3:]
        if raw_json_text.endswith("```"):
            raw_json_text = raw_json_text[:-3]
        raw_json_text = raw_json_text.strip()

        parsed_dict = json.loads(raw_json_text)
        reasoning_output = GeminiReasoningOutput(**parsed_dict)

        # Validate citations against valid IDs
        sanitized_output, warnings = validate_and_sanitize_citations(
            reasoning_output, valid_ev_ids, valid_pol_ids
        )
        return sanitized_output

    except json.JSONDecodeError as err:
        logger.error(f"Gemini returned malformed JSON: {err}")
        return create_fallback_reasoning_output(
            claim_id=package.claim_id,
            valid_evidence_ids=valid_ev_ids,
            reason=f"Gemini returned malformed JSON: {str(err)}"
        )
    except Exception as err:
        logger.error(f"Error invoking Gemini service: {err}")
        return create_fallback_reasoning_output(
            claim_id=package.claim_id,
            valid_evidence_ids=valid_ev_ids,
            reason=f"Gemini service exception: {str(err)}"
        )
