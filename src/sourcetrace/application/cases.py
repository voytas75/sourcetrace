"""Application-layer case intake contracts."""

from dataclasses import dataclass

from sourcetrace.domain.cases import Case
from sourcetrace.domain.documents import Document


@dataclass(frozen=True)
class CaseCreationRequest:
    """Input contract for opening a new investigation case."""

    case_id: str
    title: str
    description: str | None = None


@dataclass(frozen=True)
class CaseCreationOutcome:
    """Output contract for a created investigation case."""

    request: CaseCreationRequest
    case: Case


@dataclass(frozen=True)
class SourceIngestionRequest:
    """Input contract for attaching a source artifact to an existing case."""

    case_id: str
    document_id: str
    source_type: str
    source_locator: str | None = None


@dataclass(frozen=True)
class SourceIngestionOutcome:
    """Output contract for a source attached to a case."""

    request: SourceIngestionRequest
    document: Document


__all__ = [
    "CaseCreationOutcome",
    "CaseCreationRequest",
    "SourceIngestionOutcome",
    "SourceIngestionRequest",
]
