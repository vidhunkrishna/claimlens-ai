from enum import Enum
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

class ContradictionSeverity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class ContradictionStatus(str, Enum):
    REQUIRES_INVESTIGATION = "REQUIRES_INVESTIGATION"
    CONTRADICTION_DETECTED = "CONTRADICTION_DETECTED"
    POTENTIAL_MISMATCH = "POTENTIAL_MISMATCH"

class DetectionMethod(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    SEMANTIC_LLM = "SEMANTIC_LLM"

class CrossDocumentContradiction(BaseModel):
    """
    Schema for a detected cross-document contradiction with full source A vs source B provenance.
    """
    contradiction_id: str = Field(..., description="Unique contradiction identifier (e.g. CONT-CLM002-incident_date)")
    field_name: str = Field(..., description="Name of the conflicting field/fact (e.g. incident_date, driver_name)")
    source_document_a_id: str = Field(..., description="Source document A ID")
    source_document_a_type: str = Field(..., description="Source document A type (e.g. CLAIM_FORM)")
    source_value_a: Any = Field(..., description="Value extracted from document A")
    source_document_b_id: str = Field(..., description="Source document B ID")
    source_document_b_type: str = Field(..., description="Source document B type (e.g. INCIDENT_DESCRIPTION)")
    source_value_b: Any = Field(..., description="Value extracted from document B")
    severity: ContradictionSeverity = Field(..., description="Contradiction severity level (HIGH, MEDIUM, LOW)")
    explanation: str = Field(..., description="Detailed explanation of the contradiction")
    status: ContradictionStatus = Field(default=ContradictionStatus.REQUIRES_INVESTIGATION, description="Investigation status")
    detection_method: DetectionMethod = Field(..., description="DETERMINISTIC or SEMANTIC_LLM")
    confidence_score: float = Field(default=1.0, description="Detection confidence score (0.0 to 1.0)", ge=0.0, le=1.0)

class ContradictionReport(BaseModel):
    """
    Aggregated contradiction report for a claim package.
    """
    claim_id: str = Field(..., description="Claim ID evaluated")
    total_contradictions_found: int = Field(..., description="Total count of contradictions detected")
    high_severity_count: int = Field(..., description="Count of HIGH severity contradictions")
    medium_severity_count: int = Field(..., description="Count of MEDIUM severity contradictions")
    low_severity_count: int = Field(..., description="Count of LOW severity contradictions")
    contradictions: List[CrossDocumentContradiction] = Field(default_factory=list, description="List of detected contradictions")
    requires_investigator_review: bool = Field(..., description="True if any contradiction requires human investigation")
