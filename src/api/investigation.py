import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from src.models.investigation_report import ClaimInvestigationReport
from src.services.ingestion_service import (
    ingest_claim_from_directory,
    ingest_raw_claim_package
)
from src.services.investigation_engine import review_claim_package

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/investigation", tags=["Claim Investigation Pipeline"])

@router.post("/review/package", response_model=ClaimInvestigationReport)
def review_custom_package(payload: Dict[str, Any]):
    """
    Execute complete claim investigation pipeline for an in-memory custom uploaded package payload.
    """
    logger.info("POST /api/v1/investigation/review/package endpoint entered")
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload must be a JSON object"
        )

    raw_documents = payload.get("documents")
    if not isinstance(raw_documents, list) or len(raw_documents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload must contain 'documents' (non-empty list of document objects)"
        )

    claim_id = payload.get("claim_id")
    if not claim_id or claim_id == "package" or claim_id == "CLM-CUSTOM":
        inferred_id = None
        for doc in raw_documents:
            if isinstance(doc, dict) and doc.get("claim_id"):
                inferred_id = str(doc.get("claim_id")).strip()
                break
        if inferred_id:
            claim_id = inferred_id
        elif not claim_id or claim_id == "package":
            claim_id = "CLM-CUSTOM"

    ingest_res = ingest_raw_claim_package(claim_id, raw_documents)
    if ingest_res.status == "FAILED" or not ingest_res.package:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": f"Cannot review custom claim package '{claim_id}': ingestion failed",
                "errors": [err.model_dump() for err in ingest_res.errors]
            }
        )

    return review_claim_package(ingest_res.package)

@router.post("/review/{claim_id}", response_model=ClaimInvestigationReport)
def review_claim_by_id(claim_id: str):
    """
    Execute the complete evidence-backed claim investigation pipeline for a claim ID.
    Generates structured 9-section report with exact source citations.
    """
    ingest_res = ingest_claim_from_directory(claim_id)
    if ingest_res.status == "FAILED" or not ingest_res.package:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": f"Cannot review claim '{claim_id}': ingestion failed",
                "errors": [err.model_dump() for err in ingest_res.errors]
            }
        )

    return review_claim_package(ingest_res.package)
