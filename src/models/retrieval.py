from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class RetrievedClause(BaseModel):
    """
    Schema for a retrieved policy clause with exact stored text and similarity metadata.
    """
    clause_id: str = Field(..., description="Unique policy clause ID (e.g. POL-002)")
    title: str = Field(..., description="Clause section title")
    category: str = Field(..., description="Policy category (Coverage, Exclusions, Valuation, etc.)")
    exact_text: str = Field(..., description="100% exact stored policy clause text")
    similarity_score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")
    relevance_reason: str = Field(..., description="Explanation of why this clause was retrieved")
    applicable_to: List[str] = Field(default_factory=list, description="Vehicle types applicable")

class RetrievalResult(BaseModel):
    """
    Aggregated search result containing top matching policy clauses.
    """
    query: str = Field(..., description="Query text or evidence excerpt searched")
    retrieved_clauses: List[RetrievedClause] = Field(default_factory=list, description="Ordered list of retrieved clauses")
    total_results: int = Field(..., description="Total clauses returned")

class ClauseSearchRequest(BaseModel):
    """
    Payload for custom policy clause search requests.
    """
    query: str = Field(..., description="Search query string")
    top_k: int = Field(default=3, description="Number of top clauses to retrieve", ge=1, le=14)
