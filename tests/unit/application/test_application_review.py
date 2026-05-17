"""Application human review contract tests."""

from dataclasses import FrozenInstanceError

import pytest

from sourcetrace.application import ClaimReviewOutcome, ClaimReviewRequest
from sourcetrace.application.review import ClaimReviewOutcome as ModuleClaimReviewOutcome
from sourcetrace.application.review import ClaimReviewRequest as ModuleClaimReviewRequest
from sourcetrace.domain import ClaimReviewDecision, ClaimVerification
from sourcetrace.domain.types import AnalystDisposition, HumanReviewStatus, VerificationVerdict


def test_application_package_re_exports_human_review_contracts() -> None:
    assert ClaimReviewRequest is ModuleClaimReviewRequest
    assert ClaimReviewOutcome is ModuleClaimReviewOutcome


def test_claim_review_request_and_outcome_keep_verification_and_decision() -> None:
    verification = ClaimVerification(
        claim_id="claim-1",
        case_id="case-1",
        verdict=VerificationVerdict.SUPPORT,
        supporting_chunk_ids=("chunk-1",),
        contradicting_chunk_ids=(),
        analyst_notes="system-supported",
    )
    review_decision = ClaimReviewDecision(
        claim_id="claim-1",
        case_id="case-1",
        human_review_status=HumanReviewStatus.REVIEWED_ACCEPT,
        analyst_disposition=AnalystDisposition.CONFIRMED_SUPPORT,
        final_verdict=VerificationVerdict.SUPPORT,
        review_notes="Analyst confirmed support",
    )

    request = ClaimReviewRequest(verification=verification)
    outcome = ClaimReviewOutcome(request=request, review_decision=review_decision)

    assert outcome.request is request
    assert outcome.review_decision is review_decision
    assert outcome.request.verification is verification


def test_human_review_contracts_are_immutable() -> None:
    request = ClaimReviewRequest(
        verification=ClaimVerification(
            claim_id="claim-1",
            case_id="case-1",
            verdict=VerificationVerdict.SUPPORT,
        )
    )

    with pytest.raises(FrozenInstanceError):
        setattr(request, "verification", None)
