"""Application-layer document preparation contracts."""

from dataclasses import dataclass

from sourcetrace.domain.chunks import DocumentChunk
from sourcetrace.domain.documents import Document


@dataclass(frozen=True)
class DocumentPreparationRequest:
    """Input contract for preparing an ingested document for downstream analysis."""

    case_id: str
    document_id: str
    chunking_method: str | None = None


@dataclass(frozen=True)
class DocumentPreparationOutcome:
    """Output contract for a prepared document and its addressable chunks."""

    request: DocumentPreparationRequest
    document: Document
    chunks: tuple[DocumentChunk, ...]


__all__ = [
    "DocumentPreparationOutcome",
    "DocumentPreparationRequest",
]
