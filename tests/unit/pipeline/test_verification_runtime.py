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
    assert outcome.verification_outcome.publication_gate == "allowed"
    assert outcome.verification_outcome.gate_reason is None
