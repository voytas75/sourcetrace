"""Minimal application runtime for LLM-backed credibility assessment."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sourcetrace.application.credibility import (
    CredibilityAssessmentOutcome,
    CredibilityAssessmentRequest,
)
from sourcetrace.domain import DocumentCredibilityAssessment
from sourcetrace.domain.types import CredibilityBand, ProvenanceDistance

if TYPE_CHECKING:
    from sourcetrace.llm.interfaces import CredibilityDraftGateway


class _LlmCredibilityAssessor:
    def __init__(
        self,
        *,
        draft_credibility: "CredibilityDraftGateway",
        assessed_at: Callable[[], datetime],
        assessed_by: str,
    ) -> None:
        self._draft_credibility = draft_credibility
        self._assessed_at = assessed_at
        self._assessed_by = assessed_by

    def __call__(
        self,
        request: CredibilityAssessmentRequest,
    ) -> CredibilityAssessmentOutcome:
        document = request.document
        draft = self._draft_credibility(_credibility_prompt(request))
        assessment = DocumentCredibilityAssessment(
            assessment_id=f"credibility-{document.document_id}",
            document_id=document.document_id,
            source_reliability=CredibilityBand.UNKNOWN,
            information_credibility=CredibilityBand.UNKNOWN,
            source_reliability_factors=(),
            information_credibility_factors=(),
            provenance_distance=ProvenanceDistance.UNKNOWN,
            method=request.assessment_method or "llm_draft_v1",
            notes=draft.text.strip() or None,
            assessed_by=self._assessed_by,
            assessed_at=self._assessed_at(),
            override=False,
        )
        return CredibilityAssessmentOutcome(request=request, assessment=assessment)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _credibility_prompt(request: CredibilityAssessmentRequest) -> str:
    document = request.document
    lines = [
        "Draft advisory credibility notes for this source document.",
        f"Document ID: {document.document_id}",
        f"Case ID: {document.case_id}",
        f"Source type: {document.source_type}",
        f"Source URL: {document.source_url or 'unknown'}",
        f"Publisher: {document.publisher or 'unknown'}",
        f"Author: {document.author or 'unknown'}",
        f"Title: {document.title or 'unknown'}",
        "Published at: "
        f"{document.published_at.isoformat() if document.published_at else 'unknown'}",
        f"Retrieved at: {document.retrieved_at.isoformat()}",
        f"Language: {document.language or 'unknown'}",
        f"Requested method: {request.assessment_method or 'llm_draft_v1'}",
    ]
    return "\n".join(lines)


def build_llm_credibility_assessor(
    *,
    draft_credibility: "CredibilityDraftGateway",
    assessed_at: Callable[[], datetime] | None = None,
    assessed_by: str = "system",
) -> _LlmCredibilityAssessor:
    """Bind the LLM credibility draft gateway into the application assessment shape."""

    return _LlmCredibilityAssessor(
        draft_credibility=draft_credibility,
        assessed_at=assessed_at or _utc_now,
        assessed_by=assessed_by,
    )


__all__ = ["build_llm_credibility_assessor"]
