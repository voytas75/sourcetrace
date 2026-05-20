"""Application-layer credibility assessment contracts."""

from dataclasses import dataclass

from sourcetrace.domain.chunks import DocumentChunk
from sourcetrace.domain.documents import Document, DocumentCredibilityAssessment


@dataclass(frozen=True)
class CredibilityAssessmentRequest:
    """Input contract for advisory OSINT-style credibility assessment of one document."""

    document: Document
    assessment_method: str | None = None
    prepared_chunks: tuple[DocumentChunk, ...] = ()


@dataclass(frozen=True)
class CredibilityAssessmentOutcome:
    """Output contract for advisory OSINT-style credibility assessment of one document."""

    request: CredibilityAssessmentRequest
    assessment: DocumentCredibilityAssessment


__all__ = [
    "CredibilityAssessmentOutcome",
    "CredibilityAssessmentRequest",
]
