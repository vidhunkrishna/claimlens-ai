import os
import json
from typing import Dict, List, Any, Tuple
from src.models.evidence import (
    DocumentType,
    BaseDocument,
    ClaimFormDocument,
    RepairEstimateDocument,
    FIRDocument,
    IncidentDescriptionDocument,
    PolicyScheduleDocument,
    KeyDeclarationDocument,
)

DEFAULT_CLAIMS_DIR = os.path.join("data", "claims")

def load_raw_claim_from_directory(claim_id: str, claims_dir: str = DEFAULT_CLAIMS_DIR) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Load raw JSON document payloads from disk for a given claim_id.
    Returns (raw_documents_list, loading_errors_list).
    """
    claim_path = os.path.join(claims_dir, claim_id)
    if not os.path.exists(claim_path):
        return [], [f"Claim directory not found: {claim_path}"]
    
    if not os.path.isdir(claim_path):
        return [], [f"Claim path is not a directory: {claim_path}"]

    raw_docs = []
    errors = []
    
    files = sorted(os.listdir(claim_path))
    json_files = [f for f in files if f.endswith(".json")]
    
    if not json_files:
        errors.append(f"No JSON document files found in claim directory {claim_id}")
        return [], errors

    for filename in json_files:
        file_path = os.path.join(claim_path, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = json.load(f)
                if isinstance(content, dict):
                    raw_docs.append(content)
                else:
                    errors.append(f"File {filename} content is not a valid JSON object dictionary")
        except json.JSONDecodeError as err:
            errors.append(f"Malformed JSON in file {filename}: {str(err)}")
        except Exception as err:
            errors.append(f"Error reading file {filename}: {str(err)}")

    return raw_docs, errors

def parse_raw_document(raw_doc: Dict[str, Any]) -> BaseDocument:
    """
    Instantiate appropriate Pydantic document subclass from raw dictionary.
    """
    doc_type_str = str(raw_doc.get("document_type", "UNKNOWN")).upper()
    try:
        doc_type = DocumentType(doc_type_str)
    except ValueError:
        doc_type = DocumentType.UNKNOWN

    data = {
        "document_id": str(raw_doc.get("document_id", "UNKNOWN_DOC")),
        "claim_id": str(raw_doc.get("claim_id", "UNKNOWN_CLAIM")),
        "document_type": doc_type,
        "source": str(raw_doc.get("source", "Unknown")),
        "content": str(raw_doc.get("content", "")),
        "metadata": raw_doc.get("metadata", {}) if isinstance(raw_doc.get("metadata"), dict) else {}
    }

    if doc_type == DocumentType.CLAIM_FORM:
        return ClaimFormDocument(**data)
    elif doc_type == DocumentType.REPAIR_ESTIMATE:
        return RepairEstimateDocument(**data)
    elif doc_type == DocumentType.FIR:
        return FIRDocument(**data)
    elif doc_type == DocumentType.INCIDENT_DESCRIPTION:
        return IncidentDescriptionDocument(**data)
    elif doc_type == DocumentType.POLICY_SCHEDULE:
        return PolicyScheduleDocument(**data)
    elif doc_type == DocumentType.KEY_DECLARATION:
        return KeyDeclarationDocument(**data)
    else:
        return BaseDocument(**data)
