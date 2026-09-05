import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
from src.models.evidence import NormalizedClaimPackage, Fact, DocumentType, BaseDocument
from src.models.contradictions import (
    ContradictionSeverity,
    ContradictionStatus,
    DetectionMethod,
    CrossDocumentContradiction,
    ContradictionReport,
)

def _normalize_str(val: Any) -> str:
    """Normalize string for fuzzy comparison."""
    if val is None:
        return ""
    s = str(val).strip().lower()
    # Remove common punctuation
    return re.sub(r'[^\w\s]', '', s)

def _are_dates_equivalent(d1_str: str, d2_str: str) -> bool:
    """Check if two date strings represent the same date."""
    if not d1_str or not d2_str:
        return True # Missing values handled separately

    # Normalize standard YYYY-MM-DD
    s1 = _normalize_str(d1_str)
    s2 = _normalize_str(d2_str)

    if s1 == s2:
        return True

    # Try parsing ISO YYYY-MM-DD
    try:
        dt1 = datetime.strptime(d1_str.strip(), "%Y-%m-%d")
        dt2 = datetime.strptime(d2_str.strip(), "%Y-%m-%d")
        return dt1.date() == dt2.date()
    except ValueError:
        pass

    # Substring check for formatted text like "10th august 2026"
    return s1 in s2 or s2 in s1

def _are_values_equivalent(val_a: Any, val_b: Any, field_name: str) -> bool:
    """
    Determine if two values are semantically equivalent for a given field type.
    """
    if val_a is None or val_b is None:
        return True # Missing value is not a contradiction

    s_a = _normalize_str(val_a)
    s_b = _normalize_str(val_b)

    if s_a == "" or s_b == "":
        return True

    if s_a == s_b:
        return True

    # 1. Date Field
    if "date" in field_name:
        return _are_dates_equivalent(str(val_a), str(val_b))

    # 2. Location Field
    if "location" in field_name:
        # Check containment (e.g. "green acres apartment" in "basement parking green acres apartment")
        if s_a in s_b or s_b in s_a:
            return True
        # Check common city/landmark tokens
        tokens_a = set(s_a.split())
        tokens_b = set(s_b.split())
        overlap = tokens_a.intersection(tokens_b)
        # If major non-stopword tokens overlap (e.g. indiranagar metro)
        meaningful_overlap = [t for t in overlap if len(t) > 3 and t not in ["road", "street", "near", "station"]]
        if len(meaningful_overlap) >= 2:
            return True
        return False

    # 3. Vehicle Make/Model Field
    if field_name in ["make_model", "vehicle_registration"]:
        if s_a in s_b or s_b in s_a:
            return True
        return False

    # 4. Damaged Parts / Damage Description
    if field_name in ["damaged_parts", "damage_description"]:
        list_a = [str(x).lower() for x in (val_a if isinstance(val_a, list) else [val_a])]
        list_b = [str(x).lower() for x in (val_b if isinstance(val_b, list) else [val_b])]
        
        # Extract core part keywords (front, bumper, headlight, fork, rear, mudguard, tail)
        parts_a = set(re.findall(r'\b(front|rear|bumper|headlight|fork|mudguard|tail|bonnet|radiator|fender)\b', " ".join(list_a)))
        parts_b = set(re.findall(r'\b(front|rear|bumper|headlight|fork|mudguard|tail|bonnet|radiator|fender)\b', " ".join(list_b)))

        if not parts_a or not parts_b:
            return True
        
        # If front vs rear mismatch explicitly:
        if ("front" in parts_a and "rear" in parts_b) or ("rear" in parts_a and "front" in parts_b):
            return False

        if ("fork" in parts_a and "mudguard" in parts_b) or ("bumper" in parts_a and "mudguard" in parts_b):
            return False

        return len(parts_a.intersection(parts_b)) > 0

    return False

def detect_cross_document_contradictions(package: NormalizedClaimPackage) -> ContradictionReport:
    """
    Perform deterministic pairwise cross-document evidence comparisons across all documents in claim package.
    """
    contradictions: List[CrossDocumentContradiction] = []
    seen_pairs: Set[str] = set()

    # Collect documents by ID
    docs_by_id: Dict[str, BaseDocument] = {doc.document_id: doc for doc in package.documents}

    # Group facts by fact_name
    facts_by_name: Dict[str, List[Fact]] = {}
    for fact in package.facts:
        if fact.fact_name not in facts_by_name:
            facts_by_name[fact.fact_name] = []
        facts_by_name[fact.fact_name].append(fact)

    # 1. Incident Date Contradictions across documents
    date_facts = facts_by_name.get("incident_date", []) + facts_by_name.get("incident_date_mentioned", [])
    for i in range(len(date_facts)):
        for j in range(i + 1, len(date_facts)):
            fa = date_facts[i]
            fb = date_facts[j]

            if fa.document_id != fb.document_id and fa.value and fb.value:
                pair_key = f"date-{fa.document_id}-{fb.document_id}"
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    if not _are_dates_equivalent(str(fa.value), str(fb.value)):
                        doc_a = docs_by_id.get(fa.document_id)
                        doc_b = docs_by_id.get(fb.document_id)
                        contradictions.append(CrossDocumentContradiction(
                            contradiction_id=f"CONT-{package.claim_id}-incident_date-{len(contradictions)+1:03d}",
                            field_name="incident_date",
                            source_document_a_id=fa.document_id,
                            source_document_a_type=doc_a.document_type.value if doc_a else "DOCUMENT",
                            source_value_a=fa.value,
                            source_document_b_id=fb.document_id,
                            source_document_b_type=doc_b.document_type.value if doc_b else "DOCUMENT",
                            source_value_b=fb.value,
                            severity=ContradictionSeverity.HIGH,
                            explanation=f"Incident date contradiction: '{fa.source_reference}' states '{fa.value}' whereas '{fb.source_reference}' states '{fb.value}'.",
                            status=ContradictionStatus.REQUIRES_INVESTIGATION,
                            detection_method=DetectionMethod.DETERMINISTIC,
                            confidence_score=1.0
                        ))

    # 2. Repair Estimate Date Predating Incident Date Check
    est_date_facts = facts_by_name.get("estimate_date", [])
    for fa in date_facts:
        for fb in est_date_facts:
            if fa.value and fb.value:
                inc_dt = datetime.strptime(str(fa.value).strip(), "%Y-%m-%d") if re.match(r'^\d{4}-\d{2}-\d{2}$', str(fa.value)) else None
                est_dt = datetime.strptime(str(fb.value).strip(), "%Y-%m-%d") if re.match(r'^\d{4}-\d{2}-\d{2}$', str(fb.value)) else None

                if inc_dt and est_dt and est_dt.date() < inc_dt.date():
                    pair_key = f"predate-{fa.document_id}-{fb.document_id}"
                    if pair_key not in seen_pairs:
                        seen_pairs.add(pair_key)
                        doc_a = docs_by_id.get(fa.document_id)
                        doc_b = docs_by_id.get(fb.document_id)
                        contradictions.append(CrossDocumentContradiction(
                            contradiction_id=f"CONT-{package.claim_id}-estimate_predates_incident",
                            field_name="estimate_date",
                            source_document_a_id=fa.document_id,
                            source_document_a_type=doc_a.document_type.value if doc_a else "DOCUMENT",
                            source_value_a=fa.value,
                            source_document_b_id=fb.document_id,
                            source_document_b_type=doc_b.document_type.value if doc_b else "DOCUMENT",
                            source_value_b=fb.value,
                            severity=ContradictionSeverity.HIGH,
                            explanation=f"Chronological impossibility: Repair estimate date ({fb.value}) predates claimed incident date ({fa.value}).",
                            status=ContradictionStatus.REQUIRES_INVESTIGATION,
                            detection_method=DetectionMethod.DETERMINISTIC,
                            confidence_score=1.0
                        ))

    # 3. Driver Name Contradictions
    driver_facts = facts_by_name.get("driver_name", []) + facts_by_name.get("driver_name_mentioned", [])
    for i in range(len(driver_facts)):
        for j in range(i + 1, len(driver_facts)):
            fa = driver_facts[i]
            fb = driver_facts[j]
            if fa.document_id != fb.document_id and fa.value and fb.value:
                pair_key = f"driver-{fa.document_id}-{fb.document_id}"
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    if not _are_values_equivalent(fa.value, fb.value, "driver_name"):
                        doc_a = docs_by_id.get(fa.document_id)
                        doc_b = docs_by_id.get(fb.document_id)
                        contradictions.append(CrossDocumentContradiction(
                            contradiction_id=f"CONT-{package.claim_id}-driver_name",
                            field_name="driver_name",
                            source_document_a_id=fa.document_id,
                            source_document_a_type=doc_a.document_type.value if doc_a else "DOCUMENT",
                            source_value_a=fa.value,
                            source_document_b_id=fb.document_id,
                            source_document_b_type=doc_b.document_type.value if doc_b else "DOCUMENT",
                            source_value_b=fb.value,
                            severity=ContradictionSeverity.HIGH,
                            explanation=f"Driver identity mismatch: Claim Form lists driver '{fa.value}' whereas Incident Statement names '{fb.value}'.",
                            status=ContradictionStatus.REQUIRES_INVESTIGATION,
                            detection_method=DetectionMethod.DETERMINISTIC,
                            confidence_score=1.0
                        ))

    # 3b. Vehicle Registration Contradictions
    vreg_facts = facts_by_name.get("vehicle_registration", []) + facts_by_name.get("registration_number", [])
    for i in range(len(vreg_facts)):
        for j in range(i + 1, len(vreg_facts)):
            fa = vreg_facts[i]
            fb = vreg_facts[j]
            if fa.document_id != fb.document_id and fa.value and fb.value:
                pair_key = f"vreg-{fa.document_id}-{fb.document_id}"
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    if not _are_values_equivalent(fa.value, fb.value, "vehicle_registration"):
                        doc_a = docs_by_id.get(fa.document_id)
                        doc_b = docs_by_id.get(fb.document_id)
                        contradictions.append(CrossDocumentContradiction(
                            contradiction_id=f"CONT-{package.claim_id}-vehicle_registration",
                            field_name="vehicle_registration",
                            source_document_a_id=fa.document_id,
                            source_document_a_type=doc_a.document_type.value if doc_a else "DOCUMENT",
                            source_value_a=fa.value,
                            source_document_b_id=fb.document_id,
                            source_document_b_type=doc_b.document_type.value if doc_b else "DOCUMENT",
                            source_value_b=fb.value,
                            severity=ContradictionSeverity.HIGH,
                            explanation=f"Vehicle registration mismatch: '{fa.source_reference}' lists '{fa.value}' whereas '{fb.source_reference}' lists '{fb.value}'.",
                            status=ContradictionStatus.REQUIRES_INVESTIGATION,
                            detection_method=DetectionMethod.DETERMINISTIC,
                            confidence_score=1.0
                        ))

    # 4. Location Contradictions
    loc_facts = facts_by_name.get("incident_location", []) + facts_by_name.get("location_mentioned", [])
    for i in range(len(loc_facts)):
        for j in range(i + 1, len(loc_facts)):
            fa = loc_facts[i]
            fb = loc_facts[j]
            if fa.document_id != fb.document_id and fa.value and fb.value:
                pair_key = f"loc-{fa.document_id}-{fb.document_id}"
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    if not _are_values_equivalent(fa.value, fb.value, "incident_location"):
                        doc_a = docs_by_id.get(fa.document_id)
                        doc_b = docs_by_id.get(fb.document_id)
                        contradictions.append(CrossDocumentContradiction(
                            contradiction_id=f"CONT-{package.claim_id}-incident_location",
                            field_name="incident_location",
                            source_document_a_id=fa.document_id,
                            source_document_a_type=doc_a.document_type.value if doc_a else "DOCUMENT",
                            source_value_a=fa.value,
                            source_document_b_id=fb.document_id,
                            source_document_b_type=doc_b.document_type.value if doc_b else "DOCUMENT",
                            source_value_b=fb.value,
                            severity=ContradictionSeverity.HIGH,
                            explanation=f"Incident location contradiction: '{fa.source_reference}' lists '{fa.value}' whereas '{fb.source_reference}' lists '{fb.value}'.",
                            status=ContradictionStatus.REQUIRES_INVESTIGATION,
                            detection_method=DetectionMethod.DETERMINISTIC,
                            confidence_score=1.0
                        ))

    # 5. Damaged Parts vs Repair Estimate Line Items Contradictions
    cf_doc = next((d for d in package.documents if d.document_type == DocumentType.CLAIM_FORM), None)
    re_doc = next((d for d in package.documents if d.document_type == DocumentType.REPAIR_ESTIMATE), None)
    
    if cf_doc and re_doc:
        cf_parts = cf_doc.metadata.get("damaged_parts")
        re_items = [item.get("description") for item in re_doc.metadata.get("line_items", []) if isinstance(item, dict)]
        
        if cf_parts and re_items:
            if not _are_values_equivalent(cf_parts, re_items, "damaged_parts"):
                pair_key = f"parts-{cf_doc.document_id}-{re_doc.document_id}"
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    contradictions.append(CrossDocumentContradiction(
                        contradiction_id=f"CONT-{package.claim_id}-damaged_parts",
                        field_name="damaged_parts",
                        source_document_a_id=cf_doc.document_id,
                        source_document_a_type=cf_doc.document_type.value,
                        source_value_a=cf_parts,
                        source_document_b_id=re_doc.document_id,
                        source_document_b_type=re_doc.document_type.value,
                        source_value_b=re_items,
                        severity=ContradictionSeverity.HIGH,
                        explanation=f"Damaged parts mismatch: Claim Form lists '{cf_parts}' whereas Repair Estimate lists '{re_items}'.",
                        status=ContradictionStatus.REQUIRES_INVESTIGATION,
                        detection_method=DetectionMethod.DETERMINISTIC,
                        confidence_score=1.0
                    ))

    # 6. Incident Time Contradictions
    time_facts = facts_by_name.get("incident_time", []) + facts_by_name.get("incident_time_mentioned", [])
    for i in range(len(time_facts)):
        for j in range(i + 1, len(time_facts)):
            fa = time_facts[i]
            fb = time_facts[j]
            if fa.document_id != fb.document_id and fa.value and fb.value:
                pair_key = f"time-{fa.document_id}-{fb.document_id}"
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    if _normalize_str(fa.value) != _normalize_str(fb.value):
                        doc_a = docs_by_id.get(fa.document_id)
                        doc_b = docs_by_id.get(fb.document_id)
                        contradictions.append(CrossDocumentContradiction(
                            contradiction_id=f"CONT-{package.claim_id}-incident_time",
                            field_name="incident_time",
                            source_document_a_id=fa.document_id,
                            source_document_a_type=doc_a.document_type.value if doc_a else "DOCUMENT",
                            source_value_a=fa.value,
                            source_document_b_id=fb.document_id,
                            source_document_b_type=doc_b.document_type.value if doc_b else "DOCUMENT",
                            source_value_b=fb.value,
                            severity=ContradictionSeverity.MEDIUM,
                            explanation=f"Incident time mismatch: '{fa.source_reference}' states '{fa.value}' whereas '{fb.source_reference}' states '{fb.value}'.",
                            status=ContradictionStatus.REQUIRES_INVESTIGATION,
                            detection_method=DetectionMethod.DETERMINISTIC,
                            confidence_score=1.0
                        ))

    # Calculate severity counters
    high = len([c for c in contradictions if c.severity == ContradictionSeverity.HIGH])
    medium = len([c for c in contradictions if c.severity == ContradictionSeverity.MEDIUM])
    low = len([c for c in contradictions if c.severity == ContradictionSeverity.LOW])

    return ContradictionReport(
        claim_id=package.claim_id,
        total_contradictions_found=len(contradictions),
        high_severity_count=high,
        medium_severity_count=medium,
        low_severity_count=low,
        contradictions=contradictions,
        requires_investigator_review=len(contradictions) > 0
    )
