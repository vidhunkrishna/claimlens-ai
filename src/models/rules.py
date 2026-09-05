from enum import Enum
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

class RuleStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    NEEDS_INFO = "NEEDS_INFO"

class DeterministicRecommendation(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_INFORMATION = "REQUEST_INFORMATION"
    ESCALATE = "ESCALATE"

class RuleResult(BaseModel):
    """
    Structured outcome of a single deterministic rule evaluation.
    """
    rule_id: str = Field(..., description="Unique rule identifier (e.g. RULE-CLAIM-WINDOW)")
    policy_clause_id: Optional[str] = Field(None, description="Associated policy clause ID (e.g. POL-009)")
    rule_name: str = Field(..., description="Human-readable rule name")
    status: RuleStatus = Field(..., description="Rule status (PASS, FAIL, WARN, NEEDS_INFO)")
    explanation: str = Field(..., description="Detailed explanation of the rule evaluation")
    input_values: Dict[str, Any] = Field(default_factory=dict, description="Input values used during evaluation")
    source_document_ids: List[str] = Field(default_factory=list, description="Source document IDs referenced by this rule")

class RulesEvaluationReport(BaseModel):
    """
    Complete report containing all evaluated deterministic rules and overall recommendation.
    """
    claim_id: str = Field(..., description="Claim ID evaluated")
    total_rules_evaluated: int = Field(..., description="Total count of rules evaluated")
    passed_count: int = Field(..., description="Count of PASS rules")
    failed_count: int = Field(..., description="Count of FAIL rules")
    warn_count: int = Field(..., description="Count of WARN rules")
    needs_info_count: int = Field(..., description="Count of NEEDS_INFO rules")
    overall_recommendation: DeterministicRecommendation = Field(..., description="Overall deterministic recommendation")
    rule_results: List[RuleResult] = Field(default_factory=list, description="Detailed list of rule results")
