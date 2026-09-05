from typing import List, Dict, Any, Optional
from src.models.evidence import (
    NormalizedClaimPackage,
    IngestionResult,
    ValidationErrorDetail,
    BaseDocument
)
from src.services.document_loader import (
    load_raw_claim_from_directory,
    parse_raw_document,
    DEFAULT_CLAIMS_DIR
)
from src.services.document_validator import validate_claim_package_integrity
from src.services.fact_extractor import extract_facts_from_documents

def ingest_raw_claim_package(claim_id: str, raw_documents: List[Dict[str, Any]]) -> IngestionResult:
    """
    Ingest, validate, normalize, and extract facts from an in-memory raw claim package payload.
    """
    validation_errors = validate_claim_package_integrity(claim_id, raw_documents)
    
    if validation_errors:
        return IngestionResult(
            claim_id=claim_id,
            status="FAILED",
            package=None,
            errors=validation_errors
        )

    # Instantiate typed Pydantic models for each document
    documents: List[BaseDocument] = [parse_raw_document(rd) for rd in raw_documents]
    
    # Extract facts with full source provenance
    facts = extract_facts_from_documents(documents)

    package = NormalizedClaimPackage(
        claim_id=claim_id,
        documents=documents,
        facts=facts,
        is_valid=True,
        validation_errors=[]
    )

    return IngestionResult(
        claim_id=claim_id,
        status="SUCCESS",
        package=package,
        errors=[]
    )

def ingest_claim_from_directory(claim_id: str, claims_dir: str = DEFAULT_CLAIMS_DIR) -> IngestionResult:
    """
    Ingest, validate, normalize, and extract facts from a claim directory on disk.
    """
    raw_documents, load_errors = load_raw_claim_from_directory(claim_id, claims_dir)
    
    if load_errors:
        err_details = [
            ValidationErrorDetail(error_code="DOCUMENT_LOAD_ERROR", message=msg)
            for msg in load_errors
        ]
        return IngestionResult(
            claim_id=claim_id,
            status="FAILED",
            package=None,
            errors=err_details
        )

    return ingest_raw_claim_package(claim_id, raw_documents)
