import os
import json
from typing import Dict, List, Any

DEFAULT_POLICY_PATH = os.path.join("data", "policy", "motor_policy.json")
DEFAULT_CLAIMS_DIR = os.path.join("data", "claims")

def load_policy(policy_path: str = DEFAULT_POLICY_PATH) -> Dict[str, Any]:
    """
    Load and parse the motor insurance policy JSON file.
    """
    if not os.path.exists(policy_path):
        raise FileNotFoundError(f"Policy file not found at: {policy_path}")
    with open(policy_path, "r", encoding="utf-8") as f:
        return json.load(f)

def list_all_claims(claims_dir: str = DEFAULT_CLAIMS_DIR) -> List[str]:
    """
    List all claim directory IDs available in the dataset directory.
    """
    if not os.path.exists(claims_dir):
        return []
    return sorted([
        d for d in os.listdir(claims_dir)
        if os.path.isdir(os.path.join(claims_dir, d)) and d.startswith("CLM-")
    ])

def load_claim(claim_id: str, claims_dir: str = DEFAULT_CLAIMS_DIR) -> Dict[str, Any]:
    """
    Load all JSON documents associated with a specific claim ID.
    Returns a dictionary mapping document filenames to parsed JSON contents.
    """
    claim_path = os.path.join(claims_dir, claim_id)
    if not os.path.exists(claim_path):
        raise FileNotFoundError(f"Claim directory not found for ID: {claim_id}")

    documents = {}
    for filename in sorted(os.listdir(claim_path)):
        if filename.endswith(".json"):
            file_path = os.path.join(claim_path, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                doc_name = filename.replace(".json", "")
                documents[doc_name] = json.load(f)
    
    return {
        "claim_id": claim_id,
        "documents": documents
    }

def validate_dataset_integrity(policy_path: str = DEFAULT_POLICY_PATH, claims_dir: str = DEFAULT_CLAIMS_DIR) -> Dict[str, Any]:
    """
    Perform structural and rule integrity validation across the policy and claims dataset.
    Returns validation status report.
    """
    policy = load_policy(policy_path)
    policy_clauses = {c["clause_id"]: c for c in policy.get("clauses", [])}
    
    claims = list_all_claims(claims_dir)
    results = {
        "policy_clauses_count": len(policy_clauses),
        "total_claims": len(claims),
        "claim_reports": {}
    }

    for claim_id in claims:
        claim_package = load_claim(claim_id, claims_dir)
        docs = claim_package["documents"]
        
        # Mandatory document validation
        has_claim_form = "claim_form" in docs
        has_policy_schedule = "policy_schedule" in docs
        has_incident_desc = "incident_description" in docs
        
        doc_types = [doc.get("document_type") for doc in docs.values()]
        
        results["claim_reports"][claim_id] = {
            "documents_found": list(docs.keys()),
            "document_types": doc_types,
            "has_mandatory_documents": bool(has_claim_form and has_policy_schedule and has_incident_desc),
            "document_count": len(docs)
        }

    return results
