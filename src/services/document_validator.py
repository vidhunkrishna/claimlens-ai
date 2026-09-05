from typing import Dict, List, Any
from src.models.evidence import DocumentType, ValidationErrorDetail

VALID_DOC_TYPES = {dt.value for dt in DocumentType if dt != DocumentType.UNKNOWN}

def validate_claim_package_integrity(expected_claim_id: str, raw_documents: List[Dict[str, Any]]) -> List[ValidationErrorDetail]:
    """
    Validate claim package documents for schema correctness, matching claim ID,
    duplicate IDs, unsupported types, and mandatory document presence.
    """
    errors: List[ValidationErrorDetail] = []

    if not raw_documents:
        errors.append(ValidationErrorDetail(
            error_code="EMPTY_CLAIM_PACKAGE",
            message=f"No documents available for claim ID {expected_claim_id}"
        ))
        return errors

    seen_doc_ids = set()
    seen_doc_types = set()
    doc_type_counts = {}

    for idx, doc in enumerate(raw_documents):
        if not isinstance(doc, dict):
            errors.append(ValidationErrorDetail(
                error_code="MALFORMED_DOCUMENT",
                message=f"Document at index {idx} is not a valid dictionary payload"
            ))
            continue

        doc_id = doc.get("document_id")
        doc_claim_id = doc.get("claim_id")
        doc_type_raw = doc.get("document_type")

        # 1. Missing Required Top-Level Schema Fields
        required_keys = ["document_id", "claim_id", "document_type", "source", "content"]
        missing_keys = [k for k in required_keys if k not in doc or doc[k] is None or str(doc[k]).strip() == ""]
        if missing_keys:
            errors.append(ValidationErrorDetail(
                error_code="MISSING_REQUIRED_FIELDS",
                message=f"Document '{doc_id or idx}' is missing required fields: {', '.join(missing_keys)}",
                document_id=doc_id
            ))

        # 2. Wrong Claim ID Mismatch
        if doc_claim_id and str(doc_claim_id).strip() != str(expected_claim_id).strip():
            errors.append(ValidationErrorDetail(
                error_code="WRONG_CLAIM_ID",
                message=f"Document '{doc_id}' specifies claim ID '{doc_claim_id}', which does not match expected claim ID '{expected_claim_id}'",
                document_id=doc_id
            ))

        # 3. Unsupported / Unknown Document Type
        if not doc_type_raw or str(doc_type_raw).upper() not in VALID_DOC_TYPES:
            errors.append(ValidationErrorDetail(
                error_code="UNSUPPORTED_DOCUMENT_TYPE",
                message=f"Document '{doc_id}' has unsupported or invalid document type '{doc_type_raw}'",
                document_id=doc_id
            ))

        # 4. Duplicate Document ID
        if doc_id:
            if doc_id in seen_doc_ids:
                errors.append(ValidationErrorDetail(
                    error_code="DUPLICATE_DOCUMENT_ID",
                    message=f"Duplicate document ID detected: '{doc_id}'",
                    document_id=doc_id
                ))
            else:
                seen_doc_ids.add(doc_id)

        # 5. Duplicate Document Type (Single instance types: CLAIM_FORM, INCIDENT_DESCRIPTION)
        if doc_type_raw and str(doc_type_raw).upper() in VALID_DOC_TYPES:
            dt_upper = str(doc_type_raw).upper()
            doc_type_counts[dt_upper] = doc_type_counts.get(dt_upper, 0) + 1
            if dt_upper in [DocumentType.CLAIM_FORM.value, DocumentType.INCIDENT_DESCRIPTION.value] and doc_type_counts[dt_upper] > 1:
                errors.append(ValidationErrorDetail(
                    error_code="DUPLICATE_DOCUMENT_TYPE",
                    message=f"Duplicate document of type '{dt_upper}' detected in claim package",
                    document_id=doc_id
                ))

    # 6. Mandatory Document Completeness Check
    # Required: CLAIM_FORM + INCIDENT_DESCRIPTION + (REPAIR_ESTIMATE or FIR)
    has_claim_form = "CLAIM_FORM" in doc_type_counts
    has_incident_desc = "INCIDENT_DESCRIPTION" in doc_type_counts
    has_estimate_or_fir = ("REPAIR_ESTIMATE" in doc_type_counts) or ("FIR" in doc_type_counts)

    if not has_claim_form:
        errors.append(ValidationErrorDetail(
            error_code="MISSING_MANDATORY_DOCUMENT",
            message="Claim package is missing mandatory 'CLAIM_FORM' document"
        ))
    if not has_incident_desc:
        errors.append(ValidationErrorDetail(
            error_code="MISSING_MANDATORY_DOCUMENT",
            message="Claim package is missing mandatory 'INCIDENT_DESCRIPTION' document"
        ))
    if not has_estimate_or_fir:
        errors.append(ValidationErrorDetail(
            error_code="MISSING_MANDATORY_DOCUMENT",
            message="Claim package is missing mandatory evidence document: either 'REPAIR_ESTIMATE' or 'FIR' is required"
        ))

    return errors
