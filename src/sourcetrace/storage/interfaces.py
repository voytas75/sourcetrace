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
from sourcetrace.application.continuity import ContinuityPackOutcome
from sourcetrace.domain.documents import Document
from sourcetrace.domain.documents import DocumentCredibilityAssessment


class CaseRepository(Protocol):
    """Persistence seam for case aggregate metadata."""

    def save_case(self, case: Case) -> Case:
        ...

    def get_case(self, case_id: str) -> Case | None:
        ...

    def list_cases(self) -> tuple[Case, ...]:
        ...

    def save_continuity_pack(
        self,
        case_id: str,
        continuity_pack: ContinuityPackOutcome,
    ) -> ContinuityPackOutcome:
        ...

    def get_continuity_pack(self, case_id: str) -> ContinuityPackOutcome | None:
        ...

    def clear_continuity_pack(self, case_id: str) -> None:
        ...


class DocumentRepository(Protocol):
    """Persistence seam for documents and prepared chunks."""

    def save_document(self, document: Document) -> Document:
        ...

    def get_document(self, document_id: str) -> Document | None:
        ...

    def list_documents_for_case(self, case_id: str) -> tuple[Document, ...]:
        ...

    def save_chunks(self, chunks: tuple[DocumentChunk, ...]) -> tuple[DocumentChunk, ...]:
        ...

    def list_chunks_for_document(
        self,
        case_id: str,
        document_id: str,
    ) -> tuple[DocumentChunk, ...]:
        ...

    def list_chunks_for_case(self, case_id: str) -> tuple[DocumentChunk, ...]:
        ...

    def save_credibility_assessment(
        self,
        assessment: DocumentCredibilityAssessment,
    ) -> DocumentCredibilityAssessment:
        ...

    def get_credibility_assessment(
        self,
        document_id: str,
    ) -> DocumentCredibilityAssessment | None:
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

    def get_verification(self, claim_id: str) -> ClaimVerification | None:
        ...

    def save_review_decision(
        self,
        review_decision: ClaimReviewDecision,
    ) -> ClaimReviewDecision:
        ...

    def get_review_decision(self, claim_id: str) -> ClaimReviewDecision | None:
        ...

    def list_review_decisions_for_case(
        self,
        case_id: str,
    ) -> tuple[ClaimReviewDecision, ...]:
        ...

    def list_evidence_links_for_claim(
        self,
        claim_id: str,
    ) -> tuple[ClaimEvidenceLink, ...]:
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
