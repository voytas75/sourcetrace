"""Lower-level persistence dependency interfaces."""

from dataclasses import dataclass
from typing import Protocol

from sourcetrace.domain.cases import Case
from sourcetrace.domain.chunks import DocumentChunk
from sourcetrace.domain.claims import (
    Claim,
    ClaimEvidenceLink,
    ClaimReviewDecision,
    ClaimVerification,
)
from sourcetrace.domain.documents import Document


class CaseRepository(Protocol):
    """Persistence seam for case aggregate metadata."""

    def save_case(self, case: Case) -> Case:
        ...

    def get_case(self, case_id: str) -> Case | None:
        ...


class DocumentRepository(Protocol):
    """Persistence seam for documents and prepared chunks."""

    def save_document(self, document: Document) -> Document:
        ...

    def get_document(self, document_id: str) -> Document | None:
        ...

    def save_chunks(self, chunks: tuple[DocumentChunk, ...]) -> tuple[DocumentChunk, ...]:
        ...

    def list_chunks_for_document(
        self,
        case_id: str,
        document_id: str,
    ) -> tuple[DocumentChunk, ...]:
        ...


class ClaimRepository(Protocol):
    """Persistence seam for claims, evidence links, and review state."""

    def save_claims(self, claims: tuple[Claim, ...]) -> tuple[Claim, ...]:
        ...

    def get_claim(self, claim_id: str) -> Claim | None:
        ...

    def list_claims_for_case(self, case_id: str) -> tuple[Claim, ...]:
        ...

    def save_evidence_links(
        self,
        evidence_links: tuple[ClaimEvidenceLink, ...],
    ) -> tuple[ClaimEvidenceLink, ...]:
        ...

    def save_verification(self, verification: ClaimVerification) -> ClaimVerification:
        ...

    def save_review_decision(
        self,
        review_decision: ClaimReviewDecision,
    ) -> ClaimReviewDecision:
        ...


@dataclass(frozen=True)
class CorePersistence:
    """Core persistence seam bundle for explicit repository dependency wiring."""

    cases: CaseRepository
    documents: DocumentRepository
    claims: ClaimRepository


__all__ = [
    "CaseRepository",
    "ClaimRepository",
    "CorePersistence",
    "DocumentRepository",
]
