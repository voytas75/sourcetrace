from datetime import UTC, datetime

from sourcetrace.domain import (
    Case,
    Claim,
    ClaimEvidenceLink,
    ClaimReviewDecision,
    ClaimVerification,
    Document,
    DocumentCredibilityAssessment,
)
from sourcetrace.domain.types import (
    CredibilityBand,
    HumanReviewStatus,
    ProvenanceDistance,
    VerificationVerdict,
)
from sourcetrace.storage import CaseRepository, ClaimRepository, DocumentRepository
from sourcetrace.storage.memory import create_in_memory_persistence


def test_full_api_storage_protocols_define_read_and_artifact_seams() -> None:
    assert callable(CaseRepository.list_cases)
    assert callable(DocumentRepository.list_documents_for_case)
    assert callable(DocumentRepository.save_credibility_assessment)
    assert callable(DocumentRepository.get_credibility_assessment)
    assert callable(ClaimRepository.get_verification)
    assert callable(ClaimRepository.get_review_decision)
    assert callable(ClaimRepository.list_review_decisions_for_case)
    assert callable(ClaimRepository.list_evidence_links_for_claim)


def test_in_memory_storage_round_trips_full_api_read_models_and_artifacts() -> None:
    persistence = create_in_memory_persistence()
    case = Case(case_id="case-1", title="Bridge reopening")
    document = _document()
    claim = _claim()
    evidence_link = ClaimEvidenceLink(
        claim_id="claim-1",
        document_id="doc-1",
        chunk_id="chunk-1",
        evidence_rank=1,
        evidence_verdict=VerificationVerdict.SUPPORT,
        rationale="Retrieved evidence.",
        snippet="The bridge reopened after inspection.",
        score=0.9,
    )
    verification = ClaimVerification(
        claim_id="claim-1",
        case_id="case-1",
        verdict=VerificationVerdict.SUPPORT,
        supporting_chunk_ids=("chunk-1",),
    )
    review = ClaimReviewDecision(
        claim_id="claim-1",
        case_id="case-1",
        human_review_status=HumanReviewStatus.REVIEWED_ACCEPT,
        final_verdict=VerificationVerdict.SUPPORT,
    )
    assessment = DocumentCredibilityAssessment(
        assessment_id="credibility-doc-1",
        document_id="doc-1",
        source_reliability=CredibilityBand.UNKNOWN,
        information_credibility=CredibilityBand.UNKNOWN,
        source_reliability_factors=(),
        information_credibility_factors=(),
        provenance_distance=ProvenanceDistance.UNKNOWN,
        method="llm_draft_v1",
        notes="Draft credibility note.",
        assessed_by="system",
        assessed_at=datetime(2026, 5, 19, 10, 0, tzinfo=UTC),
        override=False,
    )

    persistence.cases.save_case(case)
    persistence.documents.save_document(document)
    persistence.claims.save_claims((claim,))
    persistence.claims.save_evidence_links((evidence_link,))
    persistence.claims.save_verification(verification)
    persistence.claims.save_review_decision(review)
    persistence.documents.save_credibility_assessment(assessment)

    assert persistence.cases.list_cases() == (case,)
    assert persistence.documents.list_documents_for_case("case-1") == (document,)
    assert persistence.claims.get_verification("claim-1") is verification
    assert persistence.claims.get_review_decision("claim-1") is review
    assert persistence.claims.list_review_decisions_for_case("case-1") == (review,)
    assert persistence.claims.list_evidence_links_for_claim("claim-1") == (
        evidence_link,
    )
    assert persistence.documents.get_credibility_assessment("doc-1") is assessment


def _document() -> Document:
    return Document(
        document_id="doc-1",
        case_id="case-1",
        source_type="url",
        source_url="https://example.test/bridge",
        publisher="Example News",
        author="Analyst",
        title="Bridge update",
        published_at=datetime(2026, 5, 18, 0, 0, tzinfo=UTC),
        retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
        content_hash="sha256:abc123",
        language="en",
    )


def _claim() -> Claim:
    return Claim(
        claim_id="claim-1",
        case_id="case-1",
        document_id="doc-1",
        chunk_id="chunk-1",
        exact_text="The bridge reopened after inspection.",
        source_span_reference="p1",
        system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
    )
