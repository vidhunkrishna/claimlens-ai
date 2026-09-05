from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from src.models.contradictions import ContradictionReport
from src.services.ingestion_service import (
    ingest_claim_from_directory,
    ingest_raw_claim_package
)
from src.services.contradiction_detector import detect_cross_document_contradictions

router = APIRouter(prefix="/api/v1/contradictions", tags=["Contradiction Detector"])

@router.post("/detect/{claim_id}", response_model=ContradictionReport)
def detect_claim_contradictions(claim_id: str):
    """
    Detect cross-document factual contradictions for a claim ID.
    """
    ingest_res = ingest_claim_from_directory(claim_id)
    if ingest_res.status == "FAILED" or not ingest_res.package:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": f"Cannot detect contradictions: claim '{claim_id}' failed ingestion",
                "errors": [err.model_dump() for err in ingest_res.errors]
            }
        )

    return detect_cross_document_contradictions(ingest_res.package)

@router.post("/detect/package", response_model=ContradictionReport)
def detect_custom_package_contradictions(payload: Dict[str, Any]):
    """
    Detect cross-document evidence contradictions for a custom uploaded claim package.
    """
    claim_id = payload.get("claim_id")
    raw_documents = payload.get("documents")

    if not claim_id or not isinstance(raw_documents, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload must contain 'claim_id' (string) and 'documents' (list of document objects)"
        )

    ingest_res = ingest_raw_claim_package(claim_id, raw_documents)
    if ingest_res.status == "FAILED" or not ingest_res.package:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": f"Cannot detect contradictions: custom package '{claim_id}' failed ingestion",
                "errors": [err.model_dump() for err in ingest_res.errors]
            }
        )

    return detect_cross_document_contradictions(ingest_res.package)
