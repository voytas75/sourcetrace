from dataclasses import fields, is_dataclass
from datetime import datetime, timezone

from sourcetrace.domain.documents import Document, DocumentCredibilityAssessment
from sourcetrace.domain.types import (
    INFORMATION_CREDIBILITY_FIELD,
    SOURCE_RELIABILITY_FIELD,
    CredibilityBand,
    ProvenanceDistance,
)


def test_document_is_minimal_dataclass_with_core_metadata() -> None:
    retrieved_at = datetime(2026, 5, 17, 18, 30, tzinfo=timezone.utc)
    published_at = datetime(2026, 5, 16, 9, 0, tzinfo=timezone.utc)

    document = Document(
        document_id="doc-1",
        case_id="case-1",
        source_type="url",
        source_url="https://example.com/report",
        publisher="Example Publisher",
        author="A. Reporter",
        title="Example Report",
        published_at=published_at,
        retrieved_at=retrieved_at,
        content_hash="sha256:abc123",
        language="en",
    )

    assert is_dataclass(document)
    assert document.document_id == "doc-1"
    assert document.case_id == "case-1"
    assert document.source_type == "url"
    assert document.source_url == "https://example.com/report"
    assert document.publisher == "Example Publisher"
    assert document.author == "A. Reporter"
    assert document.title == "Example Report"
    assert document.published_at is published_at
    assert document.retrieved_at is retrieved_at
    assert document.content_hash == "sha256:abc123"
    assert document.language == "en"


def test_document_credibility_assessment_stores_advisory_osint_fields() -> None:
    assessed_at = datetime(2026, 5, 17, 19, 0, tzinfo=timezone.utc)

    assessment = DocumentCredibilityAssessment(
        assessment_id="cred-1",
        document_id="doc-1",
        source_reliability=CredibilityBand.HIGH,
        information_credibility=CredibilityBand.MEDIUM,
        source_reliability_factors=("publisher_history", "institutional_source"),
        information_credibility_factors=("dated_evidence", "partial_corroboration"),
        provenance_distance=ProvenanceDistance.PRIMARY,
        method="rule_based_v1",
        notes="Needs analyst review before reporting.",
        assessed_by="system",
        assessed_at=assessed_at,
        override=False,
    )

    assert is_dataclass(assessment)
    assert assessment.assessment_id == "cred-1"
    assert assessment.document_id == "doc-1"
    assert assessment.source_reliability is CredibilityBand.HIGH
    assert assessment.information_credibility is CredibilityBand.MEDIUM
    assert assessment.source_reliability_factors == (
        "publisher_history",
        "institutional_source",
    )
    assert assessment.information_credibility_factors == (
        "dated_evidence",
        "partial_corroboration",
    )
    assert assessment.provenance_distance is ProvenanceDistance.PRIMARY
    assert assessment.method == "rule_based_v1"
    assert assessment.notes == "Needs analyst review before reporting."
    assert assessment.assessed_by == "system"
    assert assessment.assessed_at is assessed_at
    assert assessment.override is False


def test_credibility_assessment_keeps_osint_field_names() -> None:
    field_names = {field.name for field in fields(DocumentCredibilityAssessment)}

    assert SOURCE_RELIABILITY_FIELD == "source_reliability"
    assert INFORMATION_CREDIBILITY_FIELD == "information_credibility"
    assert SOURCE_RELIABILITY_FIELD in field_names
    assert INFORMATION_CREDIBILITY_FIELD in field_names
