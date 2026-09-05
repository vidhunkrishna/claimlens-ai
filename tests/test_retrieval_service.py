import time
import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.services.retrieval_service import (
    load_policy_index,
    get_clause_by_id,
    retrieve_relevant_clauses,
    retrieve_clauses_for_claim
)
from src.services.dataset_loader import load_policy, load_claim
from src.services.ingestion_service import ingest_claim_from_directory

client = TestClient(app)

def test_fast_startup_index_loading():
    """
    Test precomputed policy index loads in < 50 milliseconds to fulfill startup constraints.
    """
    start_time = time.perf_counter()
    index = load_policy_index()
    duration_ms = (time.perf_counter() - start_time) * 1000.0
    
    assert duration_ms < 50.0, f"Index loading took {duration_ms:.2f}ms, exceeding 50ms startup threshold!"
    assert len(index["clauses"]) >= 14

def test_known_policy_query():
    """
    Test query 'what accidental damage incidents are covered' retrieves POL-001 as top result.
    """
    res = retrieve_relevant_clauses("what accidental damage incidents are covered", top_k=3)
    top_clause = res.retrieved_clauses[0]
    assert top_clause.clause_id == "POL-001"
    assert top_clause.similarity_score > 0.3

def test_exclusion_query():
    """
    Test exclusion query 'drunk driving alcohol BAC' retrieves POL-002 as top result.
    """
    res = retrieve_relevant_clauses("drunk driving alcohol BAC intoxication", top_k=3)
    top_clause = res.retrieved_clauses[0]
    assert top_clause.clause_id == "POL-002"
    assert "Intoxication" in top_clause.title
    assert top_clause.similarity_score > 0.3

def test_claim_window_query():
    """
    Test claim window query 'days allowed to report claim intimation delay' retrieves POL-007 and POL-009.
    """
    res = retrieve_relevant_clauses("days allowed to report claim intimation delay window", top_k=3)
    retrieved_ids = [c.clause_id for c in res.retrieved_clauses]
    assert "POL-007" in retrieved_ids or "POL-009" in retrieved_ids

def test_required_document_query():
    """
    Test required document query 'mandatory document checklist FIR keys' retrieves POL-010 and POL-012.
    """
    res = retrieve_relevant_clauses("mandatory document checklist FIR keys surrender", top_k=3)
    retrieved_ids = [c.clause_id for c in res.retrieved_clauses]
    assert "POL-010" in retrieved_ids or "POL-012" in retrieved_ids

def test_irrelevant_query():
    """
    Test irrelevant query 'space shuttle orbital rocket launch' returns low similarity scores.
    """
    res = retrieve_relevant_clauses("space shuttle orbital rocket launch trajectory", top_k=3)
    top_score = res.retrieved_clauses[0].similarity_score
    assert top_score < 0.05, f"Expected low similarity for irrelevant query, got {top_score}"

def test_exact_clause_text_fidelity():
    """
    Verify character-for-character exact text match between retrieved clause and master motor_policy.json.
    """
    master_policy = load_policy()
    master_clauses = {c["clause_id"]: c["text"] for c in master_policy["clauses"]}
    
    for clause_id, original_text in master_clauses.items():
        retrieved = get_clause_by_id(clause_id)
        assert retrieved is not None
        assert retrieved.exact_text == original_text, f"Exact text mismatch for clause {clause_id}!"

def test_api_retrieval_endpoints():
    """
    Test FastAPI policy retrieval API endpoints.
    """
    # 1. GET /api/v1/retrieval/clauses
    res_list = client.get("/api/v1/retrieval/clauses")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 14

    # 2. GET /api/v1/retrieval/clause/POL-002
    res_single = client.get("/api/v1/retrieval/clause/POL-002")
    assert res_single.status_code == 200
    assert res_single.json()["clause_id"] == "POL-002"

    # 3. POST /api/v1/retrieval/search
    res_search = client.post("/api/v1/retrieval/search", json={"query": "intoxication alcohol", "top_k": 3})
    assert res_search.status_code == 200
    assert res_search.json()["retrieved_clauses"][0]["clause_id"] == "POL-002"
