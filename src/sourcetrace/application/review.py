"""Application-layer human review contracts."""

from dataclasses import dataclass

from sourcetrace.domain.claims import ClaimReviewDecision, ClaimVerification


@dataclass(frozen=True)
class ClaimReviewRequest:
    """Input contract for analyst review of a verified claim."""

    verification: ClaimVerification


@dataclass(frozen=True)
class ClaimReviewOutcome:
    """Output contract for analyst review of a verified claim."""

    request: ClaimReviewRequest
    review_decision: ClaimReviewDecision


__all__ = [
    "ClaimReviewOutcome",
    "ClaimReviewRequest",
]
