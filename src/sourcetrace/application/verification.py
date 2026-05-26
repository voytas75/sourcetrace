"""Application-layer claim verification contracts."""

from dataclasses import dataclass
from typing import Literal

from sourcetrace.domain.claims import Claim, ClaimVerification
from sourcetrace.domain.retrieval import RetrievalQuery, RetrievalResultSet

EvidenceSufficiency = Literal["supported", "refuted", "insufficient"]
PublicationGate = Literal["allowed", "review_required", "blocked"]


@dataclass(frozen=True)
class ClaimVerificationRequest:
    """Input contract for verifying one extracted claim against retrieved evidence."""

    claim: Claim
    retrieval_query: RetrievalQuery
    retrieved_evidence: RetrievalResultSet


@dataclass(frozen=True)
class ClaimVerificationOutcome:
    """Output contract for a verified claim."""

    request: ClaimVerificationRequest
    verification: ClaimVerification
    evidence_sufficiency: EvidenceSufficiency
    publication_gate: PublicationGate
    gate_reason: str | None = None


__all__ = [
    "ClaimVerificationOutcome",
    "ClaimVerificationRequest",
    "EvidenceSufficiency",
    "PublicationGate",
]
