from sourcetrace.application import ClaimVerificationExecution
from sourcetrace.domain import Claim, ClaimReviewDecision, DocumentChunk
from sourcetrace.domain.types import HumanReviewStatus, VerificationVerdict
from sourcetrace.pipeline import (
    ClaimVerificationRuntime,
    ClaimVerificationRuntimeRequest,
    EvidencePresenceClaimVerifier,
    LexicalChunkRetriever,
    RetrievalExecution,
)
from sourcetrace.pipeline.verification import (
    ClaimVerificationRuntime as ModuleClaimVerificationRuntime,
)
from sourcetrace.pipeline.verification import (
    ClaimVerificationRuntimeRequest as ModuleClaimVerificationRuntimeRequest,
)
from sourcetrace.pipeline.verification import (
    EvidencePresenceClaimVerifier as ModuleEvidencePresenceClaimVerifier,
)
from sourcetrace.storage import create_in_memory_persistence

import pytest


def _robustness_smoke_row(outcome) -> dict[str, str | None]:
    return {
        "verdict": outcome.verification_outcome.verification.verdict.value,
        "evidence_sufficiency": outcome.verification_outcome.evidence_sufficiency,
        "publication_gate": outcome.verification_outcome.publication_gate,
        "gate_reason": outcome.verification_outcome.gate_reason,
    }


def _build_baseline_runtime(
    *,
    chunk_id: str,
    raw_text: str,
    claim_id: str,
    exact_text: str = "The bridge reopened after inspection.",
) -> tuple[ClaimVerificationRuntime, Claim]:
    persistence = create_in_memory_persistence()
    persistence.documents.save_chunks(
        (
            DocumentChunk(
                chunk_id=chunk_id,
                case_id="case-1",
                document_id="doc-1",
                raw_text=raw_text,
                start_char=0,
                end_char=len(raw_text),
                chunk_index=1,
            ),
        )
    )
    claim = Claim(
        claim_id=claim_id,
        case_id="case-1",
        document_id="doc-1",
        chunk_id=None,
        exact_text=exact_text,
        source_span_reference="p1",
        system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
    )
    runtime = ClaimVerificationRuntime(
        persistence=persistence,
        retrieval=RetrievalExecution(
            retrieve_chunks=LexicalChunkRetriever(documents=persistence.documents)
        ),
        verification=ClaimVerificationExecution(
            verify_claim=EvidencePresenceClaimVerifier()
        ),
    )
    return runtime, claim


def _build_multi_chunk_runtime(
    *,
    chunks: tuple[tuple[str, str], ...],
    claim_id: str,
    exact_text: str = "The bridge reopened after inspection.",
) -> tuple[ClaimVerificationRuntime, Claim]:
    persistence = create_in_memory_persistence()
    persistence.documents.save_chunks(
        tuple(
            DocumentChunk(
                chunk_id=chunk_id,
                case_id="case-1",
                document_id="doc-1",
                raw_text=raw_text,
                start_char=0,
                end_char=len(raw_text),
                chunk_index=index,
            )
            for index, (chunk_id, raw_text) in enumerate(chunks, start=1)
        )
    )
    claim = Claim(
        claim_id=claim_id,
        case_id="case-1",
        document_id="doc-1",
        chunk_id=None,
        exact_text=exact_text,
        source_span_reference="p1",
        system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
    )
    runtime = ClaimVerificationRuntime(
        persistence=persistence,
        retrieval=RetrievalExecution(
            retrieve_chunks=LexicalChunkRetriever(documents=persistence.documents)
        ),
        verification=ClaimVerificationExecution(
            verify_claim=EvidencePresenceClaimVerifier()
        ),
    )
    return runtime, claim


def test_pipeline_package_re_exports_verification_runtime_path() -> None:
    assert ClaimVerificationRuntime is ModuleClaimVerificationRuntime
    assert ClaimVerificationRuntimeRequest is ModuleClaimVerificationRuntimeRequest
    assert EvidencePresenceClaimVerifier is ModuleEvidencePresenceClaimVerifier


def test_claim_verification_runtime_retrieves_verifies_and_persists_claim_path() -> None:
    persistence = create_in_memory_persistence()
    persistence.documents.save_chunks(
        (
            DocumentChunk(
                chunk_id="chunk-1",
                case_id="case-1",
                document_id="doc-1",
                raw_text="City officials confirmed the bridge reopened after inspection.",
                start_char=0,
                end_char=63,
                chunk_index=1,
            ),
        )
    )
    claim = Claim(
        claim_id="claim-1",
        case_id="case-1",
        document_id="doc-1",
        chunk_id="chunk-1",
        exact_text="The bridge reopened after inspection.",
        source_span_reference="p1",
        system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
    )
    runtime = ClaimVerificationRuntime(
        persistence=persistence,
        retrieval=RetrievalExecution(
            retrieve_chunks=LexicalChunkRetriever(documents=persistence.documents)
        ),
        verification=ClaimVerificationExecution(
            verify_claim=EvidencePresenceClaimVerifier()
        ),
    )

    outcome = runtime(
        ClaimVerificationRuntimeRequest(
            claim=claim,
            requested_k=3,
            query_id="query-1",
            retrieval_method="runtime-lexical",
        )
    )

    verification = outcome.verification_outcome.verification
    assert outcome.retrieval_query.query_id == "query-1"
    assert outcome.retrieved_evidence.returned_k == 1
    assert tuple(hit.chunk_id for hit in outcome.retrieved_evidence.hits) == ("chunk-1",)
    assert outcome.verification_outcome.evidence_sufficiency == "supported"
    assert outcome.verification_outcome.publication_gate == "allowed"
    assert outcome.verification_outcome.gate_reason is None
    assert outcome.verification_outcome.support_signals_present is True
    assert outcome.verification_outcome.conflict_signals_present is False
    assert outcome.verification_outcome.evidence_count == 1
    assert (
        outcome.verification_outcome.sufficiency_summary
        == "Supporting evidence found in 1 retrieved chunk."
    )
    assert verification.verdict is VerificationVerdict.SUPPORT
    assert verification.supporting_chunk_ids == ("chunk-1",)
    assert persistence.claims.get_claim("claim-1") is claim
    assert persistence.claims.get_verification("claim-1") is verification
    assert persistence.claims.list_evidence_links_for_claim("claim-1") == (
        outcome.evidence_links[0],
    )
    assert outcome.evidence_links[0].evidence_rank == 1
    assert outcome.evidence_links[0].evidence_verdict is VerificationVerdict.SUPPORT


def test_claim_verification_runtime_deduplicates_repeated_chunk_hits() -> None:
    persistence = create_in_memory_persistence()
    persistence.documents.save_chunks(
        (
            DocumentChunk(
                chunk_id="chunk-1",
                case_id="case-1",
                document_id="doc-1",
                raw_text="City officials confirmed the bridge reopened after inspection.",
                start_char=0,
                end_char=63,
                chunk_index=1,
            ),
        )
    )
    claim = Claim(
        claim_id="claim-1",
        case_id="case-1",
        document_id="doc-1",
        chunk_id="chunk-1",
        exact_text="The bridge reopened after inspection.",
        source_span_reference="p1",
        system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
    )
    runtime = ClaimVerificationRuntime(
        persistence=persistence,
        retrieval=RetrievalExecution(
            retrieve_chunks=LexicalChunkRetriever(documents=persistence.documents)
        ),
        verification=ClaimVerificationExecution(
            verify_claim=EvidencePresenceClaimVerifier()
        ),
    )

    outcome = runtime(
        ClaimVerificationRuntimeRequest(
            claim=claim,
            requested_k=3,
            document_ids=("doc-1", "doc-1"),
        )
    )

    assert tuple(hit.chunk_id for hit in outcome.retrieved_evidence.hits) == ("chunk-1",)
    assert outcome.verification_outcome.verification.supporting_chunk_ids == ("chunk-1",)
    assert persistence.claims.list_evidence_links_for_claim("claim-1") == (
        outcome.evidence_links[0],
    )


def test_claim_verification_runtime_persists_insufficient_evidence_without_hits() -> None:
    persistence = create_in_memory_persistence()
    claim = Claim(
        claim_id="claim-1",
        case_id="case-1",
        document_id="doc-1",
        chunk_id=None,
        exact_text="The bridge reopened after inspection.",
        source_span_reference="p1",
        system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
    )
    runtime = ClaimVerificationRuntime(
        persistence=persistence,
        retrieval=RetrievalExecution(
            retrieve_chunks=LexicalChunkRetriever(documents=persistence.documents)
        ),
        verification=ClaimVerificationExecution(
            verify_claim=EvidencePresenceClaimVerifier()
        ),
    )

    outcome = runtime(ClaimVerificationRuntimeRequest(claim=claim, requested_k=3))

    verification = outcome.verification_outcome.verification
    assert outcome.retrieved_evidence.hits == ()
    assert outcome.evidence_links == ()
    assert outcome.verification_outcome.evidence_sufficiency == "insufficient"
    assert outcome.verification_outcome.publication_gate == "review_required"
    assert outcome.verification_outcome.gate_reason == "grounding_insufficient"
    assert outcome.verification_outcome.support_signals_present is False
    assert outcome.verification_outcome.conflict_signals_present is False
    assert outcome.verification_outcome.evidence_count == 0
    assert (
        outcome.verification_outcome.sufficiency_summary
        == "No retrieved evidence established support for the claim."
    )
    assert verification.verdict is VerificationVerdict.INSUFFICIENT_EVIDENCE
    assert verification.supporting_chunk_ids == ()
    assert persistence.claims.get_verification("claim-1") is verification


def test_claim_verification_runtime_marks_excluded_review_verdict_as_blocked() -> None:
    persistence = create_in_memory_persistence()
    claim = Claim(
        claim_id="claim-1",
        case_id="case-1",
        document_id="doc-1",
        chunk_id=None,
        exact_text="The bridge reopened after inspection.",
        source_span_reference="p1",
        system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
    )
    runtime = ClaimVerificationRuntime(
        persistence=persistence,
        retrieval=RetrievalExecution(
            retrieve_chunks=LexicalChunkRetriever(documents=persistence.documents)
        ),
        verification=ClaimVerificationExecution(
            verify_claim=EvidencePresenceClaimVerifier()
        ),
    )
    persistence.claims.save_review_decision(
        ClaimReviewDecision(
            claim_id="claim-1",
            case_id="case-1",
            human_review_status=HumanReviewStatus.EXCLUDED,
            final_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
            analyst_disposition=None,
            review_notes="Excluded from publication.",
        )
    )

    outcome = runtime(ClaimVerificationRuntimeRequest(claim=claim, requested_k=3))

    assert outcome.verification_outcome.evidence_sufficiency == "insufficient"
    assert outcome.verification_outcome.publication_gate == "blocked"
    assert outcome.verification_outcome.gate_reason == "human_review_excluded"


def test_claim_verification_runtime_marks_reviewed_unverified_claim_as_no_verified_support() -> None:
    persistence = create_in_memory_persistence()
    claim = Claim(
        claim_id="claim-1",
        case_id="case-1",
        document_id="doc-1",
        chunk_id=None,
        exact_text="The bridge reopened after inspection.",
        source_span_reference="p1",
        system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
    )
    runtime = ClaimVerificationRuntime(
        persistence=persistence,
        retrieval=RetrievalExecution(
            retrieve_chunks=LexicalChunkRetriever(documents=persistence.documents)
        ),
        verification=ClaimVerificationExecution(
            verify_claim=EvidencePresenceClaimVerifier()
        ),
    )
    persistence.claims.save_review_decision(
        ClaimReviewDecision(
            claim_id="claim-1",
            case_id="case-1",
            human_review_status=HumanReviewStatus.REVIEWED_ACCEPT,
            final_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
            analyst_disposition=None,
            review_notes="No verified support found for publication.",
        )
    )

    outcome = runtime(ClaimVerificationRuntimeRequest(claim=claim, requested_k=3))

    assert outcome.verification_outcome.evidence_sufficiency == "insufficient"
    assert outcome.verification_outcome.publication_gate == "review_required"
    assert outcome.verification_outcome.gate_reason == "no_verified_support"


def test_claim_verification_runtime_marks_contradicted_verdict_as_refuted() -> None:
    persistence = create_in_memory_persistence()
    claim = Claim(
        claim_id="claim-1",
        case_id="case-1",
        document_id="doc-1",
        chunk_id=None,
        exact_text="The bridge reopened after inspection.",
        source_span_reference="p1",
        system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
    )

    def contradicting_verifier(request):
        verification = request.claim
        _ = verification
        from sourcetrace.application import ClaimVerificationOutcome, ClaimVerificationRequest
        from sourcetrace.domain import ClaimVerification

        assert isinstance(request, ClaimVerificationRequest)
        return ClaimVerificationOutcome(
            request=request,
            verification=ClaimVerification(
                claim_id=request.claim.claim_id,
                case_id=request.claim.case_id,
                verdict=VerificationVerdict.CONTRADICT,
                supporting_chunk_ids=(),
                contradicting_chunk_ids=("chunk-2",),
                analyst_notes="contradicted by retrieved evidence",
            ),
            evidence_sufficiency="supported",
            publication_gate="allowed",
        )

    runtime = ClaimVerificationRuntime(
        persistence=persistence,
        retrieval=RetrievalExecution(
            retrieve_chunks=LexicalChunkRetriever(documents=persistence.documents)
        ),
        verification=ClaimVerificationExecution(verify_claim=contradicting_verifier),
    )

    outcome = runtime(ClaimVerificationRuntimeRequest(claim=claim, requested_k=3))

    assert outcome.verification_outcome.verification.verdict is VerificationVerdict.CONTRADICT
    assert outcome.verification_outcome.evidence_sufficiency == "refuted"
    assert outcome.verification_outcome.publication_gate == "review_required"
    assert outcome.verification_outcome.gate_reason == "conflicting_evidence"
    assert outcome.verification_outcome.support_signals_present is False
    assert outcome.verification_outcome.conflict_signals_present is True
    assert outcome.verification_outcome.evidence_count == 1
    assert (
        outcome.verification_outcome.sufficiency_summary
        == "Conflicting evidence detected across 1 retrieved chunk."
    )


def test_robustness_fixture_pack_supportive_evidence_baseline() -> None:
    persistence = create_in_memory_persistence()
    persistence.documents.save_chunks(
        (
            DocumentChunk(
                chunk_id="chunk-supportive",
                case_id="case-1",
                document_id="doc-1",
                raw_text="City officials confirmed the bridge reopened after inspection.",
                start_char=0,
                end_char=63,
                chunk_index=1,
            ),
        )
    )
    claim = Claim(
        claim_id="claim-supportive",
        case_id="case-1",
        document_id="doc-1",
        chunk_id="chunk-supportive",
        exact_text="The bridge reopened after inspection.",
        source_span_reference="p1",
        system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
    )
    runtime = ClaimVerificationRuntime(
        persistence=persistence,
        retrieval=RetrievalExecution(
            retrieve_chunks=LexicalChunkRetriever(documents=persistence.documents)
        ),
        verification=ClaimVerificationExecution(
            verify_claim=EvidencePresenceClaimVerifier()
        ),
    )

    outcome = runtime(ClaimVerificationRuntimeRequest(claim=claim, requested_k=3))

    assert tuple(hit.chunk_id for hit in outcome.retrieved_evidence.hits) == (
        "chunk-supportive",
    )
    assert outcome.verification_outcome.verification.verdict is VerificationVerdict.SUPPORT
    assert outcome.verification_outcome.evidence_sufficiency == "supported"
    assert outcome.verification_outcome.publication_gate == "allowed"


def test_corroborated_partial_hits_publish_as_supported() -> None:
    runtime, claim = _build_multi_chunk_runtime(
        chunks=(
            ("chunk-corroborated-a", "The bridge reopened after repairs."),
            ("chunk-corroborated-b", "The inspection report cleared the bridge."),
        ),
        claim_id="claim-corroborated",
    )

    outcome = runtime(ClaimVerificationRuntimeRequest(claim=claim, requested_k=3))

    assert tuple(hit.chunk_id for hit in outcome.retrieved_evidence.hits) == (
        "chunk-corroborated-a",
        "chunk-corroborated-b",
    )
    assert tuple(hit.score for hit in outcome.retrieved_evidence.hits) == (0.8, 0.6)
    assert outcome.verification_outcome.verification.verdict is VerificationVerdict.SUPPORT
    assert outcome.verification_outcome.verification.supporting_chunk_ids == (
        "chunk-corroborated-a",
        "chunk-corroborated-b",
    )
    assert outcome.verification_outcome.evidence_sufficiency == "supported"
    assert outcome.verification_outcome.publication_gate == "allowed"


def test_single_partial_hit_still_does_not_publish_as_allowed() -> None:
    runtime, claim = _build_baseline_runtime(
        chunk_id="chunk-single-partial",
        raw_text="Inspectors reopened the investigation into bridge safety violations.",
        claim_id="claim-single-partial",
    )

    outcome = runtime(ClaimVerificationRuntimeRequest(claim=claim, requested_k=3))

    assert tuple(hit.chunk_id for hit in outcome.retrieved_evidence.hits) == (
        "chunk-single-partial",
    )
    assert tuple(hit.score for hit in outcome.retrieved_evidence.hits) == (0.6,)
    assert outcome.verification_outcome.verification.verdict is VerificationVerdict.INSUFFICIENT_EVIDENCE
    assert outcome.verification_outcome.publication_gate == "review_required"
    assert outcome.verification_outcome.gate_reason == "grounding_insufficient"


def test_robustness_fixture_pack_unrelated_evidence_baseline() -> None:
    persistence = create_in_memory_persistence()
    persistence.documents.save_chunks(
        (
            DocumentChunk(
                chunk_id="chunk-unrelated",
                case_id="case-1",
                document_id="doc-1",
                raw_text="The city approved a separate park renovation budget.",
                start_char=0,
                end_char=52,
                chunk_index=1,
            ),
        )
    )
    claim = Claim(
        claim_id="claim-unrelated",
        case_id="case-1",
        document_id="doc-1",
        chunk_id=None,
        exact_text="The bridge reopened after inspection.",
        source_span_reference="p1",
        system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
    )
    runtime = ClaimVerificationRuntime(
        persistence=persistence,
        retrieval=RetrievalExecution(
            retrieve_chunks=LexicalChunkRetriever(documents=persistence.documents)
        ),
        verification=ClaimVerificationExecution(
            verify_claim=EvidencePresenceClaimVerifier()
        ),
    )

    outcome = runtime(ClaimVerificationRuntimeRequest(claim=claim, requested_k=3))

    assert tuple(hit.chunk_id for hit in outcome.retrieved_evidence.hits) == (
        "chunk-unrelated",
    )
    assert outcome.verification_outcome.verification.verdict is VerificationVerdict.INSUFFICIENT_EVIDENCE
    assert outcome.verification_outcome.evidence_sufficiency == "insufficient"
    assert outcome.verification_outcome.publication_gate == "review_required"
    assert outcome.verification_outcome.gate_reason == "grounding_insufficient"
    assert outcome.evidence_links[0].chunk_id == "chunk-unrelated"


def test_robustness_fixture_pack_misleading_related_hit_baseline() -> None:
    persistence = create_in_memory_persistence()
    persistence.documents.save_chunks(
        (
            DocumentChunk(
                chunk_id="chunk-misleading",
                case_id="case-1",
                document_id="doc-1",
                raw_text="Inspectors reopened the investigation into bridge safety violations.",
                start_char=0,
                end_char=68,
                chunk_index=1,
            ),
        )
    )
    claim = Claim(
        claim_id="claim-misleading",
        case_id="case-1",
        document_id="doc-1",
        chunk_id=None,
        exact_text="The bridge reopened after inspection.",
        source_span_reference="p1",
        system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
    )
    runtime = ClaimVerificationRuntime(
        persistence=persistence,
        retrieval=RetrievalExecution(
            retrieve_chunks=LexicalChunkRetriever(documents=persistence.documents)
        ),
        verification=ClaimVerificationExecution(
            verify_claim=EvidencePresenceClaimVerifier()
        ),
    )

    outcome = runtime(ClaimVerificationRuntimeRequest(claim=claim, requested_k=3))

    assert tuple(hit.chunk_id for hit in outcome.retrieved_evidence.hits) == (
        "chunk-misleading",
    )
    assert outcome.verification_outcome.verification.verdict is VerificationVerdict.INSUFFICIENT_EVIDENCE
    assert outcome.verification_outcome.evidence_sufficiency == "insufficient"
    assert outcome.verification_outcome.publication_gate == "review_required"
    assert outcome.verification_outcome.gate_reason == "grounding_insufficient"
    assert outcome.evidence_links[0].chunk_id == "chunk-misleading"


def test_robustness_fixture_pack_conflicting_evidence_baseline() -> None:
    persistence = create_in_memory_persistence()
    claim = Claim(
        claim_id="claim-conflicting",
        case_id="case-1",
        document_id="doc-1",
        chunk_id=None,
        exact_text="The bridge reopened after inspection.",
        source_span_reference="p1",
        system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
    )

    def contradicting_verifier(request):
        from sourcetrace.application import ClaimVerificationOutcome, ClaimVerificationRequest
        from sourcetrace.domain import ClaimVerification

        assert isinstance(request, ClaimVerificationRequest)
        return ClaimVerificationOutcome(
            request=request,
            verification=ClaimVerification(
                claim_id=request.claim.claim_id,
                case_id=request.claim.case_id,
                verdict=VerificationVerdict.CONTRADICT,
                supporting_chunk_ids=(),
                contradicting_chunk_ids=("chunk-conflicting",),
                analyst_notes="conflicting fixture evidence",
            ),
            evidence_sufficiency="supported",
            publication_gate="allowed",
        )

    runtime = ClaimVerificationRuntime(
        persistence=persistence,
        retrieval=RetrievalExecution(
            retrieve_chunks=LexicalChunkRetriever(documents=persistence.documents)
        ),
        verification=ClaimVerificationExecution(verify_claim=contradicting_verifier),
    )

    outcome = runtime(ClaimVerificationRuntimeRequest(claim=claim, requested_k=3))

    assert outcome.verification_outcome.verification.verdict is VerificationVerdict.CONTRADICT
    assert outcome.verification_outcome.evidence_sufficiency == "refuted"
    assert outcome.verification_outcome.publication_gate == "review_required"
    assert outcome.verification_outcome.gate_reason == "conflicting_evidence"


def test_robustness_smoke_summary_records_current_fixture_pack_baseline() -> None:
    supportive_runtime, supportive_claim = _build_baseline_runtime(
        chunk_id="chunk-supportive",
        raw_text="City officials confirmed the bridge reopened after inspection.",
        claim_id="claim-supportive-smoke",
    )
    unrelated_runtime, unrelated_claim = _build_baseline_runtime(
        chunk_id="chunk-unrelated",
        raw_text="The city approved a separate park renovation budget.",
        claim_id="claim-unrelated-smoke",
    )
    misleading_runtime, misleading_claim = _build_baseline_runtime(
        chunk_id="chunk-misleading",
        raw_text="Inspectors reopened the investigation into bridge safety violations.",
        claim_id="claim-misleading-smoke",
    )

    supportive = supportive_runtime(
        ClaimVerificationRuntimeRequest(claim=supportive_claim, requested_k=3)
    )
    unrelated = unrelated_runtime(
        ClaimVerificationRuntimeRequest(claim=unrelated_claim, requested_k=3)
    )
    misleading_related = misleading_runtime(
        ClaimVerificationRuntimeRequest(claim=misleading_claim, requested_k=3)
    )

    persistence = create_in_memory_persistence()
    conflicting_claim = Claim(
        claim_id="claim-conflicting-smoke",
        case_id="case-1",
        document_id="doc-1",
        chunk_id=None,
        exact_text="The bridge reopened after inspection.",
        source_span_reference="p1",
        system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
    )

    def contradicting_verifier(request):
        from sourcetrace.application import ClaimVerificationOutcome, ClaimVerificationRequest
        from sourcetrace.domain import ClaimVerification

        assert isinstance(request, ClaimVerificationRequest)
        return ClaimVerificationOutcome(
            request=request,
            verification=ClaimVerification(
                claim_id=request.claim.claim_id,
                case_id=request.claim.case_id,
                verdict=VerificationVerdict.CONTRADICT,
                supporting_chunk_ids=(),
                contradicting_chunk_ids=("chunk-conflicting",),
                analyst_notes="conflicting fixture evidence",
            ),
            evidence_sufficiency="supported",
            publication_gate="allowed",
        )

    conflicting_runtime = ClaimVerificationRuntime(
        persistence=persistence,
        retrieval=RetrievalExecution(
            retrieve_chunks=LexicalChunkRetriever(documents=persistence.documents)
        ),
        verification=ClaimVerificationExecution(verify_claim=contradicting_verifier),
    )
    conflicting = conflicting_runtime(
        ClaimVerificationRuntimeRequest(claim=conflicting_claim, requested_k=3)
    )

    summary = {
        "supportive": _robustness_smoke_row(supportive),
        "unrelated": _robustness_smoke_row(unrelated),
        "misleading_related": _robustness_smoke_row(misleading_related),
        "conflicting": _robustness_smoke_row(conflicting),
    }

    assert summary == {
        "supportive": {
            "verdict": "support",
            "evidence_sufficiency": "supported",
            "publication_gate": "allowed",
            "gate_reason": None,
        },
        "unrelated": {
            "verdict": "insufficient_evidence",
            "evidence_sufficiency": "insufficient",
            "publication_gate": "review_required",
            "gate_reason": "grounding_insufficient",
        },
        "misleading_related": {
            "verdict": "insufficient_evidence",
            "evidence_sufficiency": "insufficient",
            "publication_gate": "review_required",
            "gate_reason": "grounding_insufficient",
        },
        "conflicting": {
            "verdict": "contradict",
            "evidence_sufficiency": "refuted",
            "publication_gate": "review_required",
            "gate_reason": "conflicting_evidence",
        },
    }


def test_overclaiming_guard_unrelated_fixture_should_not_publish_as_allowed() -> None:
    runtime, claim = _build_baseline_runtime(
        chunk_id="chunk-unrelated-guard",
        raw_text="The city approved a separate park renovation budget.",
        claim_id="claim-unrelated-guard",
    )

    outcome = runtime(ClaimVerificationRuntimeRequest(claim=claim, requested_k=3))

    assert outcome.verification_outcome.publication_gate != "allowed"


def test_overclaiming_guard_misleading_related_fixture_should_not_publish_as_allowed() -> None:
    runtime, claim = _build_baseline_runtime(
        chunk_id="chunk-misleading-guard",
        raw_text="Inspectors reopened the investigation into bridge safety violations.",
        claim_id="claim-misleading-guard",
    )

    outcome = runtime(ClaimVerificationRuntimeRequest(claim=claim, requested_k=3))

    assert outcome.verification_outcome.publication_gate != "allowed"
