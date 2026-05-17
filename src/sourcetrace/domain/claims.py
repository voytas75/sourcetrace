"""Claim verification domain records."""

from dataclasses import dataclass

from sourcetrace.domain.types import (
    AnalystDisposition,
    HumanReviewStatus,
    VerificationVerdict,
)


@dataclass(frozen=True)
class Claim:
    """Atomic verification unit extracted from source material."""

    claim_id: str
    case_id: str
    document_id: str
    chunk_id: str | None
    exact_text: str
    source_span_reference: str
    system_verdict: VerificationVerdict
    rationale: str | None


@dataclass(frozen=True)
class ClaimEvidenceLink:
    """Ranked evidence relation for a claim."""

    claim_id: str
    document_id: str
    chunk_id: str | None
    evidence_rank: int
    evidence_verdict: VerificationVerdict
    rationale: str | None
    snippet: str | None
    score: float | None = None


@dataclass(frozen=True)
class ClaimVerification:
    """Claim-level verification verdict contract."""

    claim_id: str
    case_id: str
    verdict: VerificationVerdict
    supporting_chunk_ids: tuple[str, ...] = ()
    contradicting_chunk_ids: tuple[str, ...] = ()
    analyst_notes: str | None = None


@dataclass(frozen=True)
class ClaimReviewDecision:
    """Human review outcome for a claim."""

    claim_id: str
    case_id: str
    human_review_status: HumanReviewStatus
    analyst_disposition: AnalystDisposition | None = None
    final_verdict: VerificationVerdict | None = None
    review_notes: str | None = None


@dataclass(frozen=True)
class ClaimReportEntry:
    """Report-ready claim summary contract."""

    claim_id: str
    case_id: str
    final_verdict: VerificationVerdict
    human_review_status: HumanReviewStatus
    summary_text: str
    supporting_chunk_ids: tuple[str, ...] = ()
    contradicting_chunk_ids: tuple[str, ...] = ()


__all__ = [
    "Claim",
    "ClaimEvidenceLink",
    "ClaimReportEntry",
    "ClaimReviewDecision",
    "ClaimVerification",
]
