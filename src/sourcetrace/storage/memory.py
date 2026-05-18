"""In-memory persistence adapters for the first runtime path."""

from sourcetrace.domain.cases import Case
from sourcetrace.domain.chunks import DocumentChunk
from sourcetrace.domain.claims import (
    Claim,
    ClaimEvidenceLink,
    ClaimReviewDecision,
    ClaimVerification,
)
from sourcetrace.domain.documents import Document
from sourcetrace.storage.interfaces import CorePersistence


class InMemoryCaseRepository:
    """Case repository backed by process-local dictionaries."""

    def __init__(self) -> None:
        self._cases: dict[str, Case] = {}

    def save_case(self, case: Case) -> Case:
        self._cases[case.case_id] = case
        return case

    def get_case(self, case_id: str) -> Case | None:
        return self._cases.get(case_id)


class InMemoryDocumentRepository:
    """Document and chunk repository backed by process-local dictionaries."""

    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}
        self._chunks_by_id: dict[str, DocumentChunk] = {}
        self._chunk_ids_by_document: dict[tuple[str, str], list[str]] = {}

    def save_document(self, document: Document) -> Document:
        self._documents[document.document_id] = document
        return document

    def get_document(self, document_id: str) -> Document | None:
        return self._documents.get(document_id)

    def save_chunks(self, chunks: tuple[DocumentChunk, ...]) -> tuple[DocumentChunk, ...]:
        for chunk in chunks:
            self._chunks_by_id[chunk.chunk_id] = chunk
            key = (chunk.case_id, chunk.document_id)
            document_chunk_ids = self._chunk_ids_by_document.setdefault(key, [])
            if chunk.chunk_id not in document_chunk_ids:
                document_chunk_ids.append(chunk.chunk_id)
        return chunks

    def list_chunks_for_document(
        self,
        case_id: str,
        document_id: str,
    ) -> tuple[DocumentChunk, ...]:
        chunk_ids = self._chunk_ids_by_document.get((case_id, document_id), ())
        chunks = (self._chunks_by_id[chunk_id] for chunk_id in chunk_ids)
        return tuple(sorted(chunks, key=lambda chunk: chunk.chunk_index))

    def list_chunks_for_case(self, case_id: str) -> tuple[DocumentChunk, ...]:
        chunks = (
            chunk
            for chunk in self._chunks_by_id.values()
            if chunk.case_id == case_id
        )
        return tuple(
            sorted(chunks, key=lambda chunk: (chunk.document_id, chunk.chunk_index))
        )


class InMemoryClaimRepository:
    """Claim repository backed by process-local dictionaries."""

    def __init__(self) -> None:
        self._claims: dict[str, Claim] = {}
        self._claim_ids_by_case: dict[str, list[str]] = {}
        self._evidence_links_by_claim: dict[str, list[ClaimEvidenceLink]] = {}
        self._verifications: dict[str, ClaimVerification] = {}
        self._review_decisions: dict[str, ClaimReviewDecision] = {}

    def save_claims(self, claims: tuple[Claim, ...]) -> tuple[Claim, ...]:
        for claim in claims:
            self._claims[claim.claim_id] = claim
            case_claim_ids = self._claim_ids_by_case.setdefault(claim.case_id, [])
            if claim.claim_id not in case_claim_ids:
                case_claim_ids.append(claim.claim_id)
        return claims

    def get_claim(self, claim_id: str) -> Claim | None:
        return self._claims.get(claim_id)

    def list_claims_for_case(self, case_id: str) -> tuple[Claim, ...]:
        claim_ids = self._claim_ids_by_case.get(case_id, ())
        return tuple(self._claims[claim_id] for claim_id in claim_ids)

    def save_evidence_links(
        self,
        evidence_links: tuple[ClaimEvidenceLink, ...],
    ) -> tuple[ClaimEvidenceLink, ...]:
        for evidence_link in evidence_links:
            claim_links = self._evidence_links_by_claim.setdefault(
                evidence_link.claim_id,
                [],
            )
            claim_links.append(evidence_link)
        return evidence_links

    def save_verification(self, verification: ClaimVerification) -> ClaimVerification:
        self._verifications[verification.claim_id] = verification
        return verification

    def save_review_decision(
        self,
        review_decision: ClaimReviewDecision,
    ) -> ClaimReviewDecision:
        self._review_decisions[review_decision.claim_id] = review_decision
        return review_decision

    def list_evidence_links_for_claim(
        self,
        claim_id: str,
    ) -> tuple[ClaimEvidenceLink, ...]:
        return tuple(self._evidence_links_by_claim.get(claim_id, ()))

    def get_verification(self, claim_id: str) -> ClaimVerification | None:
        return self._verifications.get(claim_id)

    def get_review_decision(self, claim_id: str) -> ClaimReviewDecision | None:
        return self._review_decisions.get(claim_id)


def create_in_memory_persistence() -> CorePersistence:
    """Build the core persistence bundle from in-memory repositories."""

    return CorePersistence(
        cases=InMemoryCaseRepository(),
        documents=InMemoryDocumentRepository(),
        claims=InMemoryClaimRepository(),
    )


__all__ = [
    "InMemoryCaseRepository",
    "InMemoryClaimRepository",
    "InMemoryDocumentRepository",
    "create_in_memory_persistence",
]
