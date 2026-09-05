from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from src.models.evidence import IngestionResult
from src.services.ingestion_service import (
    ingest_claim_from_directory,
    ingest_raw_claim_package
)
from src.services.dataset_loader import list_all_claims

router = APIRouter(prefix="/api/v1/ingest", tags=["Ingestion"])

@router.get("/claims", response_model=List[str])
def list_claims():
    """
    List all available claim package IDs in the local data repository.
    """
    return list_all_claims()

@router.post("/{claim_id}", response_model=IngestionResult)
def ingest_claim_by_id(claim_id: str):
    """
    Ingest, validate, normalize, and extract facts for a specific claim ID from disk.
    """
    result = ingest_claim_from_directory(claim_id)
    if result.status == "FAILED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": f"Ingestion failed for claim ID '{claim_id}'",
                "errors": [err.model_dump() for err in result.errors]
            }
        )
    return result

@router.post("/package", response_model=IngestionResult)
def ingest_custom_package(payload: Dict[str, Any]):
    """
    Ingest and normalize an arbitrary raw claim package payload.
    Expected JSON format: {"claim_id": "CLM-XXX", "documents": [...]}
    """
    claim_id = payload.get("claim_id")
    raw_documents = payload.get("documents")

    if not claim_id or not isinstance(raw_documents, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload must contain 'claim_id' (string) and 'documents' (list of document objects)"
        )

    result = ingest_raw_claim_package(claim_id, raw_documents)
    if result.status == "FAILED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": f"Ingestion failed for custom claim package '{claim_id}'",
                "errors": [err.model_dump() for err in result.errors]
            }
        )
    return result
