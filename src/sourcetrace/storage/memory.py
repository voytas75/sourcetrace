"""In-memory persistence adapters for the first runtime path."""

from sourcetrace.application.continuity import ContinuityPackOutcome
from sourcetrace.domain.cases import Case
from sourcetrace.domain.chunks import DocumentChunk
from sourcetrace.domain.claims import (
    Claim,
    ClaimEvidenceLink,
    ClaimReviewDecision,
    ClaimVerification,
)
from sourcetrace.domain.documents import Document
from sourcetrace.domain.documents import DocumentCredibilityAssessment
from sourcetrace.storage.interfaces import CorePersistence


class InMemoryCaseRepository:
    """Case repository backed by process-local dictionaries."""

    def __init__(self) -> None:
        self._cases: dict[str, Case] = {}
        self._continuity_packs: dict[str, ContinuityPackOutcome] = {}
        self._latest_previous_continuity_packs: dict[str, ContinuityPackOutcome] = {}
    def save_case(self, case: Case) -> Case:
        self._cases[case.case_id] = case
        return case

    def get_case(self, case_id: str) -> Case | None:
        return self._cases.get(case_id)

    def list_cases(self) -> tuple[Case, ...]:
        return tuple(
            self._cases[case_id]
            for case_id in sorted(self._cases)
        )

    def save_continuity_pack(
        self,
        case_id: str,
        continuity_pack: ContinuityPackOutcome,
    ) -> ContinuityPackOutcome:
        existing = self._continuity_packs.get(case_id)
        if existing is not None:
            self._latest_previous_continuity_packs[case_id] = existing
        self._continuity_packs[case_id] = continuity_pack
        return continuity_pack

    def get_continuity_pack(self, case_id: str) -> ContinuityPackOutcome | None:
        return self._continuity_packs.get(case_id)

    def get_latest_previous_continuity_pack(
        self,
        case_id: str,
    ) -> ContinuityPackOutcome | None:
        return self._latest_previous_continuity_packs.get(case_id)

    def clear_continuity_pack(self, case_id: str) -> None:
        self._continuity_packs.pop(case_id, None)


class InMemoryDocumentRepository:
    """Document and chunk repository backed by process-local dictionaries."""

    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}
        self._chunks_by_id: dict[str, DocumentChunk] = {}
        self._chunk_ids_by_document: dict[tuple[str, str], list[str]] = {}
        self._credibility_assessments: dict[str, DocumentCredibilityAssessment] = {}

    def save_document(self, document: Document) -> Document:
        self._documents[document.document_id] = document
        return document

    def get_document(self, document_id: str) -> Document | None:
        return self._documents.get(document_id)

    def list_documents_for_case(self, case_id: str) -> tuple[Document, ...]:
        documents = (
            document
            for document in self._documents.values()
            if document.case_id == case_id
        )
        return tuple(sorted(documents, key=lambda document: document.document_id))

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

    def save_credibility_assessment(
        self,
        assessment: DocumentCredibilityAssessment,
    ) -> DocumentCredibilityAssessment:
        self._credibility_assessments[assessment.document_id] = assessment
        return assessment

    def get_credibility_assessment(
        self,
        document_id: str,
    ) -> DocumentCredibilityAssessment | None:
        return self._credibility_assessments.get(document_id)


class InMemoryClaimRepository:
    """Claim repository backed by process-local dictionaries."""

    def __init__(self) -> None:
        self._claims: dict[str, Claim] = {}
        self._claim_ids_by_case: dict[str, list[str]] = {}
        self._evidence_links_by_claim: dict[str, list[ClaimEvidenceLink]] = {}
        self._verifications: dict[str, ClaimVerification] = {}
        self._review_decisions: dict[str, ClaimReviewDecision] = {}

    def save_claims(self, claims: tuple[Claim, ...]) -> tuple[Claim, ...]:
        persisted_claims: list[Claim] = []
        for claim in claims:
            existing_claim = self._claims.get(claim.claim_id)
            if existing_claim is None:
                persisted_claim = claim
            elif existing_claim.case_id == claim.case_id and existing_claim.document_id == claim.document_id:
                persisted_claim = claim
            else:
                persisted_claim = Claim(
                    claim_id=f"{claim.case_id}:{claim.claim_id}",
                    case_id=claim.case_id,
                    document_id=claim.document_id,
                    chunk_id=claim.chunk_id,
                    exact_text=claim.exact_text,
                    source_span_reference=claim.source_span_reference,
                    system_verdict=claim.system_verdict,
                    rationale=claim.rationale,
                )
            self._claims[persisted_claim.claim_id] = persisted_claim
            case_claim_ids = self._claim_ids_by_case.setdefault(persisted_claim.case_id, [])
            if persisted_claim.claim_id not in case_claim_ids:
                case_claim_ids.append(persisted_claim.claim_id)
            persisted_claims.append(persisted_claim)
        return tuple(persisted_claims)

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

    def list_review_decisions_for_case(
        self,
        case_id: str,
    ) -> tuple[ClaimReviewDecision, ...]:
        decisions = (
            decision
            for decision in self._review_decisions.values()
            if decision.case_id == case_id
        )
        return tuple(sorted(decisions, key=lambda decision: decision.claim_id))


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
