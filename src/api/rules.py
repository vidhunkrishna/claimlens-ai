from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from src.models.rules import RulesEvaluationReport
from src.services.ingestion_service import (
    ingest_claim_from_directory,
    ingest_raw_claim_package
)
from src.services.rules_engine import evaluate_deterministic_rules

router = APIRouter(prefix="/api/v1/rules", tags=["Rules Engine"])

@router.post("/evaluate/{claim_id}", response_model=RulesEvaluationReport)
def evaluate_rules_for_claim(claim_id: str):
    """
    Ingest claim package from disk and evaluate all deterministic insurance rules.
    """
    ingest_res = ingest_claim_from_directory(claim_id)
    if ingest_res.status == "FAILED" or not ingest_res.package:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": f"Cannot evaluate rules: claim package '{claim_id}' failed ingestion",
                "errors": [err.model_dump() for err in ingest_res.errors]
            }
        )

    return evaluate_deterministic_rules(ingest_res.package)

@router.post("/evaluate/package", response_model=RulesEvaluationReport)
def evaluate_rules_for_custom_package(payload: Dict[str, Any]):
    """
    Ingest an arbitrary raw claim package payload and evaluate all deterministic rules.
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
                "message": f"Cannot evaluate rules: custom claim package '{claim_id}' failed ingestion",
                "errors": [err.model_dump() for err in ingest_res.errors]
            }
        )

    return evaluate_deterministic_rules(ingest_res.package)
