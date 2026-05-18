"""Runtime orchestration for claim verification."""

from dataclasses import dataclass

from sourcetrace.application.interfaces import ClaimVerificationExecution
from sourcetrace.application.verification import (
    ClaimVerificationOutcome,
    ClaimVerificationRequest,
)
from sourcetrace.domain.claims import Claim, ClaimEvidenceLink, ClaimVerification
from sourcetrace.domain.retrieval import RetrievalQuery, RetrievalResultSet
from sourcetrace.domain.types import VerificationVerdict
from sourcetrace.pipeline.interfaces import RetrievalExecution
from sourcetrace.storage.interfaces import CorePersistence


@dataclass(frozen=True)
class ClaimVerificationRuntimeRequest:
    """Input for verifying one claim through retrieval and persistence."""

    claim: Claim
    requested_k: int
    query_id: str | None = None
    retrieval_method: str | None = None
    document_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClaimVerificationRuntimeOutcome:
    """Output from the first narrow verification runtime path."""

    retrieval_query: RetrievalQuery
    retrieved_evidence: RetrievalResultSet
    verification_outcome: ClaimVerificationOutcome
    evidence_links: tuple[ClaimEvidenceLink, ...]


@dataclass(frozen=True)
class EvidencePresenceClaimVerifier:
    """Minimal verifier that treats retrieved chunks as supporting evidence."""

    def __call__(self, request: ClaimVerificationRequest) -> ClaimVerificationOutcome:
        supporting_chunk_ids = tuple(
            hit.chunk_id for hit in request.retrieved_evidence.hits
        )
        verdict = (
            VerificationVerdict.SUPPORT
            if supporting_chunk_ids
            else VerificationVerdict.INSUFFICIENT_EVIDENCE
        )
        verification = ClaimVerification(
            claim_id=request.claim.claim_id,
            case_id=request.claim.case_id,
            verdict=verdict,
            supporting_chunk_ids=supporting_chunk_ids,
            contradicting_chunk_ids=(),
            analyst_notes=_verification_note(len(supporting_chunk_ids)),
        )
        return ClaimVerificationOutcome(
            request=request,
            verification=verification,
        )


@dataclass(frozen=True)
class ClaimVerificationRuntime:
    """Wire retrieval, application verification, and persistence for one claim."""

    persistence: CorePersistence
    retrieval: RetrievalExecution
    verification: ClaimVerificationExecution

    def __call__(
        self,
        request: ClaimVerificationRuntimeRequest,
    ) -> ClaimVerificationRuntimeOutcome:
        claim = request.claim
        retrieval_query = _build_retrieval_query(request)
        retrieved_evidence = self.retrieval.retrieve_chunks(retrieval_query)
        verification_request = ClaimVerificationRequest(
            claim=claim,
            retrieval_query=retrieval_query,
            retrieved_evidence=retrieved_evidence,
        )
        verification_outcome = self.verification.verify_claim(verification_request)
        evidence_links = _build_evidence_links(
            claim,
            retrieved_evidence,
            verification_outcome.verification.verdict,
        )

        self.persistence.claims.save_claims((claim,))
        self.persistence.claims.save_evidence_links(evidence_links)
        self.persistence.claims.save_verification(verification_outcome.verification)

        return ClaimVerificationRuntimeOutcome(
            retrieval_query=retrieval_query,
            retrieved_evidence=retrieved_evidence,
            verification_outcome=verification_outcome,
            evidence_links=evidence_links,
        )


def _build_retrieval_query(
    request: ClaimVerificationRuntimeRequest,
) -> RetrievalQuery:
    claim = request.claim
    document_ids = request.document_ids or (claim.document_id,)
    return RetrievalQuery(
        query_id=request.query_id or f"{claim.claim_id}:verification",
        case_id=claim.case_id,
        query_text=claim.exact_text,
        requested_k=request.requested_k,
        retrieval_method=request.retrieval_method,
        document_ids=document_ids,
    )


def _build_evidence_links(
    claim: Claim,
    retrieved_evidence: RetrievalResultSet,
    verdict: VerificationVerdict,
) -> tuple[ClaimEvidenceLink, ...]:
    return tuple(
        ClaimEvidenceLink(
            claim_id=claim.claim_id,
            document_id=hit.document_id,
            chunk_id=hit.chunk_id,
            evidence_rank=hit.rank,
            evidence_verdict=verdict,
            rationale="Retrieved by first-pass verification runtime.",
            snippet=hit.snippet,
            score=hit.score,
        )
        for hit in retrieved_evidence.hits
    )


def _verification_note(supporting_count: int) -> str:
    if supporting_count == 1:
        return "1 retrieved evidence chunk."
    return f"{supporting_count} retrieved evidence chunks."


__all__ = [
    "ClaimVerificationRuntime",
    "ClaimVerificationRuntimeOutcome",
    "ClaimVerificationRuntimeRequest",
    "EvidencePresenceClaimVerifier",
]
