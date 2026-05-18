"""Application-layer claim extraction contracts."""

from dataclasses import dataclass

from sourcetrace.domain.chunks import DocumentChunk
from sourcetrace.domain.claims import Claim, ClaimEvidenceLink
from sourcetrace.domain.documents import Document


@dataclass(frozen=True)
class ClaimExtractionRequest:
    """Input contract for extracting structured claims from a prepared document."""

    case_id: str
    document_id: str
    chunk_ids: tuple[str, ...]
    extraction_method: str | None = None


@dataclass(frozen=True)
class ClaimExtractionOutcome:
    """Output contract for extracted claims and their initial evidence links."""

    request: ClaimExtractionRequest
    document: Document
    chunks: tuple[DocumentChunk, ...]
    claims: tuple[Claim, ...]
    evidence_links: tuple[ClaimEvidenceLink, ...]
    dropped_claim_items: int = 0
    dropped_evidence_items: int = 0


__all__ = [
    "ClaimExtractionOutcome",
    "ClaimExtractionRequest",
]
