from typing import List, Any
from src.models.evidence import BaseDocument, Fact, DocumentType

def extract_facts_from_documents(documents: List[BaseDocument]) -> List[Fact]:
    """
    Extract normalized facts from a list of BaseDocument objects.
    Preserves 100% source provenance for every extracted fact.
    """
    facts: List[Fact] = []

    for doc in documents:
        # 1. Extract metadata facts
        if isinstance(doc.metadata, dict):
            for field_name, value in doc.metadata.items():
                if value is not None:
                    fact_id = f"FACT-{doc.document_id}-{field_name}"
                    source_ref = f"metadata.{field_name}"
                    
                    # Generate concise snippet text for provenance
                    if isinstance(value, (list, dict)):
                        snippet = f"{field_name}: {value}"
                    else:
                        snippet = str(value)

                    facts.append(Fact(
                        fact_id=fact_id,
                        claim_id=doc.claim_id,
                        document_id=doc.document_id,
                        document_type=doc.document_type,
                        fact_name=field_name,
                        value=value,
                        source_reference=source_ref,
                        source_text=snippet
                    ))

        # 2. Extract primary text content snippet fact
        if doc.content and len(doc.content.strip()) > 0:
            facts.append(Fact(
                fact_id=f"FACT-{doc.document_id}-content_statement",
                claim_id=doc.claim_id,
                document_id=doc.document_id,
                document_type=doc.document_type,
                fact_name="content_statement",
                value=doc.content,
                source_reference="content",
                source_text=doc.content[:150] + ("..." if len(doc.content) > 150 else "")
            ))

    return facts
