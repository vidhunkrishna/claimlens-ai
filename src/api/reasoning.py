from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from src.models.gemini_reasoning import GeminiReasoningOutput
from src.services.ingestion_service import (
    ingest_claim_from_directory,
    ingest_raw_claim_package
)
from src.services.gemini_service import analyze_claim_with_gemini

router = APIRouter(prefix="/api/v1/reasoning", tags=["Gemini Reasoning"])

@router.post("/analyze/{claim_id}", response_model=GeminiReasoningOutput)
def analyze_claim_reasoning(claim_id: str):
    """
    Perform semantic evidence reasoning and policy clause analysis using Gemini AI.
    Falls back gracefully if Gemini API is unavailable or unconfigured.
    """
    ingest_res = ingest_claim_from_directory(claim_id)
    if ingest_res.status == "FAILED" or not ingest_res.package:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": f"Cannot run reasoning: claim package '{claim_id}' failed ingestion",
                "errors": [err.model_dump() for err in ingest_res.errors]
            }
        )

    return analyze_claim_with_gemini(ingest_res.package)

@router.post("/analyze/package", response_model=GeminiReasoningOutput)
def analyze_custom_package_reasoning(payload: Dict[str, Any]):
    """
    Perform Gemini evidence reasoning for an arbitrary uploaded claim package payload.
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
                "message": f"Cannot run reasoning: custom package '{claim_id}' failed ingestion",
                "errors": [err.model_dump() for err in ingest_res.errors]
            }
        )

    return analyze_claim_with_gemini(ingest_res.package)
