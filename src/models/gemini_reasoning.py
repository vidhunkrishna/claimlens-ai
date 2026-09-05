from enum import Enum
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

class ReasoningStatus(str, Enum):
    CONFIDENT = "CONFIDENT"
    UNCERTAIN = "UNCERTAIN"
    CONTRADICTION_DETECTED = "CONTRADICTION_DETECTED"
    FALLBACK = "FALLBACK"

class ContradictionSeverity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class ClauseEffect(str, Enum):
    SUPPORTS = "SUPPORTS"
    BLOCKS = "BLOCKS"
    NEUTRAL = "NEUTRAL"
    REQUIRES_CLARIFICATION = "REQUIRES_CLARIFICATION"

class ReasoningAction(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_INFORMATION = "REQUEST_INFORMATION"
    ESCALATE = "ESCALATE"

class ContradictionFinding(BaseModel):
    """
    Represents a single semantic evidence contradiction found across documents.
    """
    finding_id: str = Field(..., description="Unique identifier for the contradiction")
    title: str = Field(..., description="Short summary title of the contradiction")
    description: str = Field(..., description="Detailed description of conflicting evidence")
    evidence_id_a: str = Field(..., description="First evidence/document ID involved (e.g. DOC-CLM002-CF)")
    evidence_id_b: str = Field(..., description="Second evidence/document ID involved (e.g. DOC-CLM002-ID)")
    severity: ContradictionSeverity = Field(..., description="Severity of the contradiction")

class PolicyClauseAnalysis(BaseModel):
    """
    Represents Gemini's reasoning regarding how a specific policy clause applies.
    """
    clause_id: str = Field(..., description="Policy clause ID (e.g. POL-002)")
    relevance: str = Field(..., description="Why this policy clause applies to the evidence")
    effect: ClauseEffect = Field(..., description="Effect of this clause on the claim outcome")
    explanation: str = Field(..., description="Detailed explanation of clause application")
    cited_evidence_ids: List[str] = Field(default_factory=list, description="List of evidence IDs cited for this clause analysis")

class GeminiReasoningOutput(BaseModel):
    """
    Structured reasoning outcome returned by Gemini AI or fallback service.
    """
    reasoning_status: ReasoningStatus = Field(..., description="Status of LLM reasoning evaluation")
    investigator_summary: str = Field(..., description="Structured investigator synthesis paragraph")
    semantic_contradictions: List[ContradictionFinding] = Field(default_factory=list, description="List of detected evidence contradictions")
    policy_analysis: List[PolicyClauseAnalysis] = Field(default_factory=list, description="List of policy clause evaluations")
    recommended_action: ReasoningAction = Field(..., description="Recommended claim action")
    requires_human_escalation: bool = Field(..., description="True if case must be escalated to a human investigator")
    escalation_reason: Optional[str] = Field(None, description="Reason for human escalation if required")
    cited_evidence_ids: List[str] = Field(default_factory=list, description="All evidence IDs cited across findings")
    cited_policy_clause_ids: List[str] = Field(default_factory=list, description="All policy clause IDs cited across findings")
