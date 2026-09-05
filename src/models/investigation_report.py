from enum import Enum
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from src.models.rules import RuleResult
from src.models.contradictions import CrossDocumentContradiction

class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"

class ExecutiveResult(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_INFORMATION = "REQUEST INFORMATION"
    ESCALATE_FOR_INVESTIGATION = "ESCALATE FOR INVESTIGATION"

class ClaimOverview(BaseModel):
    claim_id: str = Field(..., description="Unique Claim ID")
    vehicle_registration: str = Field(..., description="Vehicle Registration Number")
    vehicle_make_model: str = Field(..., description="Make and Model")
    vehicle_type: str = Field(..., description="Car or Two-Wheeler")
    claim_type: str = Field(..., description="Accidental Damage or Total Theft")
    incident_date: str = Field(..., description="Date of Incident")
    intimation_date: str = Field(..., description="Date Claim Intimated")
    insured_name: str = Field(..., description="Policyholder Name")
    idv: float = Field(..., description="Insured Declared Value")
    estimated_amount: float = Field(..., description="Estimated Claim Amount")

class DocumentCompletenessSummary(BaseModel):
    has_claim_form: bool = Field(..., description="True if Claim Form submitted")
    has_fir_or_estimate: bool = Field(..., description="True if Repair Estimate or FIR submitted")
    has_incident_description: bool = Field(..., description="True if Incident Description submitted")
    is_complete: bool = Field(..., description="True if all required documents present")
    submitted_documents: List[Dict[str, str]] = Field(default_factory=list, description="List of submitted docs (id, type, source)")
    missing_documents: List[str] = Field(default_factory=list, description="List of missing document types")

class ConsistencyAnalysisSummary(BaseModel):
    consistent_facts_count: int = Field(..., description="Count of verified consistent facts")
    contradictions_count: int = Field(..., description="Count of contradictions detected")
    contradictions: List[CrossDocumentContradiction] = Field(default_factory=list, description="List of detected contradictions")

class PolicyAnalysisItem(BaseModel):
    clause_id: str = Field(..., description="Policy Clause ID (e.g. POL-002)")
    title: str = Field(..., description="Clause Title")
    exact_clause_text: str = Field(..., description="100% exact stored policy text")
    effect: str = Field(..., description="SUPPORTS, BLOCKS, or NEUTRAL")
    explanation: str = Field(..., description="Rationale for clause application")
    cited_evidence_ids: List[str] = Field(default_factory=list, description="Evidence IDs cited")

class EvidenceFinding(BaseModel):
    finding_id: str = Field(..., description="Finding ID")
    title: str = Field(..., description="Finding Title")
    severity: str = Field(..., description="HIGH, MEDIUM, or LOW")
    explanation: str = Field(..., description="Explanation")
    source_document_id: str = Field(..., description="Source Document ID")
    source_document_type: str = Field(..., description="Source Document Type")
    exact_source_text: str = Field(..., description="Exact text excerpt retrieved from source document")
    policy_clause_id: Optional[str] = Field(None, description="Associated Policy Clause ID if applicable")
    confidence: ConfidenceLevel = Field(ConfidenceLevel.HIGH, description="Confidence in finding status")

class HumanEscalationDetail(BaseModel):
    requires_human_review: bool = Field(..., description="True if human investigator review is required")
    reason: str = Field(..., description="High-level reason for escalation decision")
    escalation_points: List[str] = Field(default_factory=list, description="Specific Bullet points explaining why human review is required")

class ClaimInvestigationReport(BaseModel):
    """
    Structured 9-Section Final Claim Investigation Report.
    """
    executive_result: ExecutiveResult = Field(..., description="1. Executive Result (APPROVE, REJECT, REQUEST INFORMATION, ESCALATE)")
    overall_confidence: ConfidenceLevel = Field(..., description="Explicit Evidence Confidence Level (HIGH, MEDIUM, LOW, UNKNOWN)")
    confidence_explanation: str = Field(..., description="Explanation for confidence level classification")
    claim_overview: ClaimOverview = Field(..., description="2. Claim Overview")
    document_completeness: DocumentCompletenessSummary = Field(..., description="3. Document Completeness")
    consistency_analysis: ConsistencyAnalysisSummary = Field(..., description="4. Consistency Analysis")
    policy_analysis: List[PolicyAnalysisItem] = Field(default_factory=list, description="5. Policy Analysis with Exact Clause Text")
    rule_results: List[RuleResult] = Field(default_factory=list, description="6. Deterministic Rule Results")
    evidence_findings: List[EvidenceFinding] = Field(default_factory=list, description="7. Itemized Findings with Exact Source Excerpts")
    recommendation_rationale: str = Field(..., description="8. Evidence-Derived Recommendation Rationale")
    human_escalation: HumanEscalationDetail = Field(..., description="9. Human Escalation Rationale & Points")

