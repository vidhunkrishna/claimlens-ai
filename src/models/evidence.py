from enum import Enum
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

class DocumentType(str, Enum):
    CLAIM_FORM = "CLAIM_FORM"
    REPAIR_ESTIMATE = "REPAIR_ESTIMATE"
    FIR = "FIR"
    INCIDENT_DESCRIPTION = "INCIDENT_DESCRIPTION"
    POLICY_SCHEDULE = "POLICY_SCHEDULE"
    KEY_DECLARATION = "KEY_DECLARATION"
    UNKNOWN = "UNKNOWN"

class Fact(BaseModel):
    """
    Extracted fact model preserving 100% source provenance.
    """
    fact_id: str = Field(..., description="Unique fact identifier")
    claim_id: str = Field(..., description="Target claim ID")
    document_id: str = Field(..., description="Source document ID")
    document_type: DocumentType = Field(..., description="Type of source document")
    fact_name: str = Field(..., description="Canonical fact name/key")
    value: Any = Field(..., description="Fact value (string, number, list, bool, etc.)")
    source_reference: str = Field(..., description="Traceable field path or document section reference")
    source_text: Optional[str] = Field(None, description="Direct text snippet supporting this fact")

class BaseDocument(BaseModel):
    """
    Base representation for any ingested claim document.
    """
    document_id: str = Field(..., description="Unique document ID")
    claim_id: str = Field(..., description="Associated claim ID")
    document_type: DocumentType = Field(..., description="Normalized document type")
    source: str = Field(..., description="Source system or submitter")
    content: str = Field(..., description="Full text content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Structured key-value metadata")

class ClaimFormDocument(BaseDocument):
    document_type: DocumentType = DocumentType.CLAIM_FORM

class RepairEstimateDocument(BaseDocument):
    document_type: DocumentType = DocumentType.REPAIR_ESTIMATE

class FIRDocument(BaseDocument):
    document_type: DocumentType = DocumentType.FIR

class IncidentDescriptionDocument(BaseDocument):
    document_type: DocumentType = DocumentType.INCIDENT_DESCRIPTION

class PolicyScheduleDocument(BaseDocument):
    document_type: DocumentType = DocumentType.POLICY_SCHEDULE

class KeyDeclarationDocument(BaseDocument):
    document_type: DocumentType = DocumentType.KEY_DECLARATION

class NormalizedClaimPackage(BaseModel):
    """
    Aggregated claim package containing all normalized documents and extracted facts.
    """
    claim_id: str = Field(..., description="Claim ID")
    documents: List[BaseDocument] = Field(default_factory=list, description="List of validated documents")
    facts: List[Fact] = Field(default_factory=list, description="Flat list of extracted facts with provenance")
    is_valid: bool = Field(True, description="True if claim package passes structural validation")
    validation_errors: List[str] = Field(default_factory=list, description="List of validation errors if invalid")

class ValidationErrorDetail(BaseModel):
    error_code: str = Field(..., description="Machine readable error code")
    message: str = Field(..., description="Human readable description of the validation error")
    document_id: Optional[str] = Field(None, description="Affected document ID if applicable")

class IngestionResult(BaseModel):
    claim_id: str
    status: str = Field(..., description="'SUCCESS' or 'FAILED'")
    package: Optional[NormalizedClaimPackage] = None
    errors: List[ValidationErrorDetail] = Field(default_factory=list)
