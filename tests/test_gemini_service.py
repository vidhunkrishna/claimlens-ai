import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from src.api.main import app
from src.services.ingestion_service import ingest_claim_from_directory
from src.services.gemini_service import (
    analyze_claim_with_gemini,
    create_fallback_reasoning_output
)
from src.models.gemini_reasoning import (
    ReasoningStatus,
    ReasoningAction,
    ContradictionSeverity,
    ClauseEffect,
    GeminiReasoningOutput
)
from src.services.citation_validator import validate_and_sanitize_citations

client = TestClient(app)

@pytest.fixture
def sample_package():
    ingest_res = ingest_claim_from_directory("CLM-001")
    assert ingest_res.status == "SUCCESS"
    return ingest_res.package

@pytest.fixture
def contradiction_package():
    ingest_res = ingest_claim_from_directory("CLM-002")
    assert ingest_res.status == "SUCCESS"
    return ingest_res.package

def test_missing_api_key_fallback(monkeypatch, sample_package):
    """
    Test that when GEMINI_API_KEY is missing, the service returns a graceful fallback without crashing.
    """
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setattr("src.core.config.settings.GEMINI_API_KEY", "")
    output = analyze_claim_with_gemini(sample_package, api_key_override="")
    assert output.reasoning_status == ReasoningStatus.FALLBACK
    assert output.requires_human_escalation is True
    assert output.recommended_action == ReasoningAction.ESCALATE
    assert "missing or unconfigured" in output.escalation_reason

def test_valid_gemini_response(sample_package):
    """
    Test parsing a valid, well-structured Gemini JSON response.
    """
    valid_json = {
        "reasoning_status": "CONFIDENT",
        "investigator_summary": "Evidence for CLM-001 is complete and consistent across DOC-CLM001-CF, DOC-CLM001-RE, and DOC-CLM001-ID.",
        "semantic_contradictions": [],
        "policy_analysis": [
            {
                "clause_id": "POL-001",
                "relevance": "Accidental external collision coverage",
                "effect": "SUPPORTS",
                "explanation": "Pillar scraping falls under accidental external means.",
                "cited_evidence_ids": ["DOC-CLM001-CF", "DOC-CLM001-ID"]
            }
        ],
        "recommended_action": "APPROVE",
        "requires_human_escalation": False,
        "escalation_reason": None,
        "cited_evidence_ids": ["DOC-CLM001-CF", "DOC-CLM001-RE", "DOC-CLM001-ID"],
        "cited_policy_clause_ids": ["POL-001"]
    }

    mock_response = MagicMock()
    mock_response.text = json.dumps(valid_json)

    with patch("google.genai.Client") as MockGenaiClient:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        MockGenaiClient.return_value = mock_client

        output = analyze_claim_with_gemini(sample_package, api_key_override="fake-test-key")
        assert output.reasoning_status == ReasoningStatus.CONFIDENT
        assert output.recommended_action == ReasoningAction.APPROVE
        assert output.requires_human_escalation is False
        assert len(output.policy_analysis) == 1
        assert output.policy_analysis[0].clause_id == "POL-001"

        # Verify that generate_content was called with settings.GEMINI_MODEL
        from src.core.config import settings
        call_kwargs = mock_client.models.generate_content.call_args.kwargs
        assert call_kwargs["model"] == settings.GEMINI_MODEL

def test_malformed_json_response(sample_package):
    """
    Test graceful fallback when Gemini returns malformed non-JSON output.
    """
    mock_response = MagicMock()
    mock_response.text = "NOT A VALID JSON STRING {{{ ::: "

    with patch("google.genai.Client") as MockGenaiClient:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        MockGenaiClient.return_value = mock_client

        output = analyze_claim_with_gemini(sample_package, api_key_override="fake-test-key")
        assert output.reasoning_status == ReasoningStatus.FALLBACK
        assert output.requires_human_escalation is True
        assert output.recommended_action == ReasoningAction.ESCALATE
        assert "malformed JSON" in output.escalation_reason

def test_missing_fields_response(sample_package):
    """
    Test graceful fallback when Gemini returns JSON missing required Pydantic schema fields.
    """
    incomplete_json = {
        "reasoning_status": "CONFIDENT"
        # Missing required investigator_summary, recommended_action, etc.
    }
    mock_response = MagicMock()
    mock_response.text = json.dumps(incomplete_json)

    with patch("google.genai.Client") as MockGenaiClient:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        MockGenaiClient.return_value = mock_client

        output = analyze_claim_with_gemini(sample_package, api_key_override="fake-test-key")
        assert output.reasoning_status == ReasoningStatus.FALLBACK
        assert output.requires_human_escalation is True
        assert output.recommended_action == ReasoningAction.ESCALATE

def test_unsupported_citation_sanitization(sample_package):
    """
    Test that hallucinated/unsupported citations (e.g. DOC-999, POL-999) are sanitized and escalated.
    """
    hallucinated_json = {
        "reasoning_status": "CONFIDENT",
        "investigator_summary": "Summary",
        "semantic_contradictions": [],
        "policy_analysis": [
            {
                "clause_id": "POL-999", # Hallucinated clause!
                "relevance": "Non-existent clause",
                "effect": "SUPPORTS",
                "explanation": "Explanation",
                "cited_evidence_ids": ["DOC-CLM001-CF", "DOC-999"] # DOC-999 is hallucinated!
            }
        ],
        "recommended_action": "APPROVE",
        "requires_human_escalation": False,
        "escalation_reason": None,
        "cited_evidence_ids": ["DOC-CLM001-CF", "DOC-999"], # DOC-999 is hallucinated!
        "cited_policy_clause_ids": ["POL-001", "POL-999"] # POL-999 is hallucinated!
    }

    mock_response = MagicMock()
    mock_response.text = json.dumps(hallucinated_json)

    with patch("google.genai.Client") as MockGenaiClient:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        MockGenaiClient.return_value = mock_client

        output = analyze_claim_with_gemini(sample_package, api_key_override="fake-test-key")
        assert output.reasoning_status == ReasoningStatus.UNCERTAIN
        assert output.requires_human_escalation is True
        assert output.recommended_action == ReasoningAction.ESCALATE
        assert "DOC-999" not in output.cited_evidence_ids
        assert "POL-999" not in output.cited_policy_clause_ids

def test_uncertain_response(contradiction_package):
    """
    Test parsing a valid response where Gemini detects contradiction/uncertainty and recommends escalation.
    """
    uncertain_json = {
        "reasoning_status": "CONTRADICTION_DETECTED",
        "investigator_summary": "Unresolvable contradictions detected between DOC-CLM002-CF and DOC-CLM002-ID.",
        "semantic_contradictions": [
            {
                "finding_id": "CONT-001",
                "title": "Incident Date & Driver Mismatch",
                "description": "Claim Form states 15th Aug by Suresh, statement states 18th Aug by Priya.",
                "evidence_id_a": "DOC-CLM002-CF",
                "evidence_id_b": "DOC-CLM002-ID",
                "severity": "HIGH"
            }
        ],
        "policy_analysis": [],
        "recommended_action": "REQUEST_INFORMATION",
        "requires_human_escalation": True,
        "escalation_reason": "Contradiction in incident dates and driver identity.",
        "cited_evidence_ids": ["DOC-CLM002-CF", "DOC-CLM002-ID"],
        "cited_policy_clause_ids": ["POL-009"]
    }

    mock_response = MagicMock()
    mock_response.text = json.dumps(uncertain_json)

    with patch("google.genai.Client") as MockGenaiClient:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        MockGenaiClient.return_value = mock_client

        output = analyze_claim_with_gemini(contradiction_package, api_key_override="fake-test-key")
        assert output.reasoning_status == ReasoningStatus.CONTRADICTION_DETECTED
        assert output.requires_human_escalation is True
        assert output.recommended_action == ReasoningAction.REQUEST_INFORMATION
        assert len(output.semantic_contradictions) == 1

def test_gemini_timeout_or_api_exception(sample_package):
    """
    Test graceful fallback when Gemini Client raises a Timeout or API exception.
    """
    with patch("google.genai.Client") as MockGenaiClient:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_exception = Exception("Connection Timeout after 10000ms")
        mock_client.models.generate_content.side_effect = Exception("Connection Timeout after 10000ms")
        MockGenaiClient.return_value = mock_client

        output = analyze_claim_with_gemini(sample_package, api_key_override="fake-test-key")
        assert output.reasoning_status == ReasoningStatus.FALLBACK
        assert output.requires_human_escalation is True
        assert output.recommended_action == ReasoningAction.ESCALATE
        assert "Gemini service exception" in output.escalation_reason

def test_api_reasoning_endpoint_fallback(monkeypatch):
    """
    Test API endpoint POST /api/v1/reasoning/analyze/CLM-001 returns fallback when API key is missing.
    """
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setattr("src.core.config.settings.GEMINI_API_KEY", "")
    res = client.post("/api/v1/reasoning/analyze/CLM-001")
    assert res.status_code == 200
    data = res.json()
    assert data["reasoning_status"] == "FALLBACK"
    assert data["requires_human_escalation"] is True
    assert data["recommended_action"] == "ESCALATE"

def test_gemini_model_configuration_and_override(monkeypatch, sample_package):
    """
    Test that analyze_claim_with_gemini uses settings.GEMINI_MODEL and respects environment variable overrides.
    """
    from src.core.config import settings
    custom_model = "gemini-2.0-flash-exp"
    monkeypatch.setattr(settings, "GEMINI_MODEL", custom_model)

    valid_json = {
        "reasoning_status": "CONFIDENT",
        "investigator_summary": "Summary",
        "semantic_contradictions": [],
        "policy_analysis": [],
        "recommended_action": "APPROVE",
        "requires_human_escalation": False,
        "escalation_reason": None,
        "cited_evidence_ids": [],
        "cited_policy_clause_ids": []
    }

    mock_response = MagicMock()
    mock_response.text = json.dumps(valid_json)

    with patch("google.genai.Client") as MockGenaiClient:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        MockGenaiClient.return_value = mock_client

        output = analyze_claim_with_gemini(sample_package, api_key_override="fake-test-key")
        assert output.reasoning_status == ReasoningStatus.CONFIDENT

        mock_client.models.generate_content.assert_called_once()
        call_kwargs = mock_client.models.generate_content.call_args.kwargs
        assert call_kwargs["model"] == custom_model

