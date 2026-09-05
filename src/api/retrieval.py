from typing import List
from fastapi import APIRouter, HTTPException, status
from src.models.retrieval import RetrievedClause, RetrievalResult, ClauseSearchRequest
from src.services.retrieval_service import (
    load_policy_index,
    get_clause_by_id,
    retrieve_relevant_clauses,
    retrieve_clauses_for_claim
)
from src.services.ingestion_service import ingest_claim_from_directory

router = APIRouter(prefix="/api/v1/retrieval", tags=["Policy Retrieval (RAG)"])

@router.get("/clauses", response_model=List[RetrievedClause])
def list_all_policy_clauses():
    """
    List all precomputed policy clauses with exact stored text.
    """
    index = load_policy_index()
    results = []
    for c in index.get("clauses", []):
        results.append(RetrievedClause(
            clause_id=c["clause_id"],
            title=c["title"],
            category=c["category"],
            exact_text=c["exact_text"],
            similarity_score=1.0,
            relevance_reason="Policy Master Index Entry",
            applicable_to=c.get("applicable_to", [])
        ))
    return results

@router.get("/clause/{clause_id}", response_model=RetrievedClause)
def get_single_clause(clause_id: str):
    """
    Retrieve exact character-for-character policy clause text by ID (e.g. POL-002).
    """
    clause = get_clause_by_id(clause_id.upper())
    if not clause:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy clause ID '{clause_id}' not found in master policy index"
        )
    return clause

@router.post("/search", response_model=RetrievalResult)
def search_policy_clauses(request: ClauseSearchRequest):
    """
    Search policy clauses using precomputed vector embeddings and cosine similarity.
    """
    return retrieve_relevant_clauses(request.query, top_k=request.top_k)

@router.post("/claim/{claim_id}", response_model=RetrievalResult)
def retrieve_clauses_for_claim_id(claim_id: str, top_k: int = 5):
    """
    Retrieve relevant policy clauses for a specific ingested claim package.
    """
    ingest_res = ingest_claim_from_directory(claim_id)
    if ingest_res.status == "FAILED" or not ingest_res.package:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot retrieve policy clauses: claim '{claim_id}' failed ingestion"
        )

    return retrieve_clauses_for_claim(ingest_res.package, top_k=top_k)
