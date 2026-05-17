"""Application-layer claim verification contracts."""

from dataclasses import dataclass

from sourcetrace.domain.claims import Claim, ClaimVerification
from sourcetrace.domain.retrieval import RetrievalQuery, RetrievalResultSet


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


__all__ = [
    "ClaimVerificationOutcome",
    "ClaimVerificationRequest",
]
