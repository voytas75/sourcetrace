from dataclasses import FrozenInstanceError, is_dataclass

import pytest

from sourcetrace.domain.claims import (
    Claim,
    ClaimEvidenceLink,
    ClaimReportEntry,
    ClaimReviewDecision,
    ClaimVerification,
)
from sourcetrace.domain.types import (
    AnalystDisposition,
    HumanReviewStatus,
    VerificationVerdict,
)


def test_claim_records_are_importable_from_claims_module() -> None:
    import sourcetrace.domain.claims as claims

    assert claims.Claim is Claim
    assert claims.ClaimEvidenceLink is ClaimEvidenceLink
    assert claims.ClaimReportEntry is ClaimReportEntry
    assert claims.ClaimReviewDecision is ClaimReviewDecision
    assert claims.ClaimVerification is ClaimVerification


def test_claim_is_minimal_dataclass_with_core_verification_fields() -> None:
    claim = Claim(
        claim_id="claim-1",
        case_id="case-1",
        document_id="doc-1",
        chunk_id="chunk-1",
        exact_text="The bridge reopened on May 17, 2026.",
        source_span_reference="doc-1:chunk-1:chars=10-49",
        system_verdict=VerificationVerdict.SUPPORT,
        rationale="The source sentence directly states the reopening date.",
    )

    assert is_dataclass(claim)
    assert claim.claim_id == "claim-1"
    assert claim.case_id == "case-1"
    assert claim.document_id == "doc-1"
    assert claim.chunk_id == "chunk-1"
    assert claim.exact_text == "The bridge reopened on May 17, 2026."
    assert claim.source_span_reference == "doc-1:chunk-1:chars=10-49"
    assert claim.system_verdict is VerificationVerdict.SUPPORT
    assert claim.rationale == "The source sentence directly states the reopening date."


def test_claim_evidence_link_stores_ranked_evidence_relationship() -> None:
    link = ClaimEvidenceLink(
        claim_id="claim-1",
        document_id="doc-2",
        chunk_id="chunk-7",
        evidence_rank=1,
        evidence_verdict=VerificationVerdict.CONTRADICT,
        rationale="The evidence gives a different reopening date.",
        snippet="Officials said the bridge remains closed until June.",
        score=0.82,
    )

    assert is_dataclass(link)
    assert link.claim_id == "claim-1"
    assert link.document_id == "doc-2"
    assert link.chunk_id == "chunk-7"
    assert link.evidence_rank == 1
    assert link.evidence_verdict is VerificationVerdict.CONTRADICT
    assert link.rationale == "The evidence gives a different reopening date."
    assert link.snippet == "Officials said the bridge remains closed until June."
    assert link.score == 0.82


def test_claim_evidence_link_score_is_optional() -> None:
    link = ClaimEvidenceLink(
        claim_id="claim-1",
        document_id="doc-3",
        chunk_id=None,
        evidence_rank=2,
        evidence_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
        snippet=None,
    )

    assert link.score is None


def test_claim_verification_stores_minimal_verdict_contract() -> None:
    verification = ClaimVerification(
        claim_id="claim-1",
        case_id="case-1",
        verdict=VerificationVerdict.SUPPORT,
        supporting_chunk_ids=("chunk-1", "chunk-2"),
        contradicting_chunk_ids=("chunk-3",),
        analyst_notes="Evidence supports the claim.",
    )

    assert is_dataclass(verification)
    assert verification.claim_id == "claim-1"
    assert verification.case_id == "case-1"
    assert verification.verdict is VerificationVerdict.SUPPORT
    assert verification.supporting_chunk_ids == ("chunk-1", "chunk-2")
    assert verification.contradicting_chunk_ids == ("chunk-3",)
    assert verification.analyst_notes == "Evidence supports the claim."


def test_claim_verification_optional_fields_default_to_absent() -> None:
    verification = ClaimVerification(
        claim_id="claim-1",
        case_id="case-1",
        verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
    )

    assert verification.supporting_chunk_ids == ()
    assert verification.contradicting_chunk_ids == ()
    assert verification.analyst_notes is None


def test_claim_verification_is_frozen() -> None:
    verification = ClaimVerification(
        claim_id="claim-1",
        case_id="case-1",
        verdict=VerificationVerdict.CONTRADICT,
    )

    with pytest.raises(FrozenInstanceError):
        verification.verdict = VerificationVerdict.SUPPORT


def test_claim_review_decision_stores_human_review_outcome() -> None:
    decision = ClaimReviewDecision(
        claim_id="claim-1",
        case_id="case-1",
        human_review_status=HumanReviewStatus.REVIEWED_OVERRIDE,
        analyst_disposition=AnalystDisposition.CONFIRMED_CONTRADICTION,
        final_verdict=VerificationVerdict.CONTRADICT,
        review_notes="Analyst overrode the system verdict after review.",
    )

    assert is_dataclass(decision)
    assert decision.claim_id == "claim-1"
    assert decision.case_id == "case-1"
    assert decision.human_review_status is HumanReviewStatus.REVIEWED_OVERRIDE
    assert decision.analyst_disposition is AnalystDisposition.CONFIRMED_CONTRADICTION
    assert decision.final_verdict is VerificationVerdict.CONTRADICT
    assert decision.review_notes == "Analyst overrode the system verdict after review."


def test_claim_review_decision_optional_fields_default_to_absent() -> None:
    decision = ClaimReviewDecision(
        claim_id="claim-1",
        case_id="case-1",
        human_review_status=HumanReviewStatus.UNREVIEWED,
    )

    assert decision.analyst_disposition is None
    assert decision.final_verdict is None
    assert decision.review_notes is None


def test_claim_review_decision_is_frozen() -> None:
    decision = ClaimReviewDecision(
        claim_id="claim-1",
        case_id="case-1",
        human_review_status=HumanReviewStatus.REVIEWED_ACCEPT,
    )

    with pytest.raises(FrozenInstanceError):
        decision.review_notes = "Cannot mutate frozen review decisions."


def test_claim_report_entry_stores_report_ready_claim_summary() -> None:
    entry = ClaimReportEntry(
        claim_id="claim-1",
        case_id="case-1",
        final_verdict=VerificationVerdict.SUPPORT,
        human_review_status=HumanReviewStatus.REVIEWED_ACCEPT,
        summary_text="The bridge reopening claim is supported by official updates.",
        supporting_chunk_ids=("chunk-1", "chunk-2"),
        contradicting_chunk_ids=("chunk-3",),
    )

    assert is_dataclass(entry)
    assert entry.claim_id == "claim-1"
    assert entry.case_id == "case-1"
    assert entry.final_verdict is VerificationVerdict.SUPPORT
    assert entry.human_review_status is HumanReviewStatus.REVIEWED_ACCEPT
    assert (
        entry.summary_text
        == "The bridge reopening claim is supported by official updates."
    )
    assert entry.supporting_chunk_ids == ("chunk-1", "chunk-2")
    assert entry.contradicting_chunk_ids == ("chunk-3",)


def test_claim_report_entry_chunk_ids_default_to_empty_tuples() -> None:
    entry = ClaimReportEntry(
        claim_id="claim-1",
        case_id="case-1",
        final_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        human_review_status=HumanReviewStatus.UNREVIEWED,
        summary_text="Evidence is not sufficient for a final finding.",
    )

    assert entry.supporting_chunk_ids == ()
    assert entry.contradicting_chunk_ids == ()


def test_claim_report_entry_is_frozen() -> None:
    entry = ClaimReportEntry(
        claim_id="claim-1",
        case_id="case-1",
        final_verdict=VerificationVerdict.CONTRADICT,
        human_review_status=HumanReviewStatus.REVIEWED_OVERRIDE,
        summary_text="The claim conflicts with the reviewed evidence.",
    )

    with pytest.raises(FrozenInstanceError):
        entry.summary_text = "Cannot mutate frozen report entries."
