"""Document domain records."""

from dataclasses import dataclass
from datetime import datetime

from sourcetrace.domain.types import CredibilityBand, ProvenanceDistance


@dataclass(frozen=True)
class Document:
    """Raw source artifact metadata."""

    document_id: str
    case_id: str
    source_type: str
    source_url: str | None
    publisher: str | None
    author: str | None
    title: str | None
    published_at: datetime | None
    retrieved_at: datetime
    content_hash: str
    language: str | None


@dataclass(frozen=True)
class DocumentCredibilityAssessment:
    """Advisory OSINT-style credibility metadata for a document."""

    assessment_id: str
    document_id: str
    source_reliability: CredibilityBand
    information_credibility: CredibilityBand
    source_reliability_factors: tuple[str, ...]
    information_credibility_factors: tuple[str, ...]
    provenance_distance: ProvenanceDistance
    method: str
    notes: str | None
    summary: str | None = None
    strengths: tuple[str, ...] = ()
    concerns: tuple[str, ...] = ()
    verification_checks: tuple[str, ...] = ()
    assessed_by: str = "system"
    assessed_at: datetime | None = None
    override: bool = False


__all__ = [
    "Document",
    "DocumentCredibilityAssessment",
]
