"""Application verification contract tests."""

from dataclasses import FrozenInstanceError

import pytest

from sourcetrace.application import ClaimVerificationOutcome, ClaimVerificationRequest
from sourcetrace.application.verification import (
    ClaimVerificationOutcome as ModuleClaimVerificationOutcome,
)
from sourcetrace.application.verification import (
    ClaimVerificationRequest as ModuleClaimVerificationRequest,
)
from sourcetrace.domain import Claim, ClaimVerification, RetrievalHit, RetrievalQuery, RetrievalResultSet
from sourcetrace.domain.types import VerificationVerdict


def test_application_package_re_exports_verification_contracts() -> None:
    assert ClaimVerificationRequest is ModuleClaimVerificationRequest
    assert ClaimVerificationOutcome is ModuleClaimVerificationOutcome


def test_claim_verification_request_keeps_claim_and_retrieval_context() -> None:
    claim = Claim(
        claim_id="claim-1",
        case_id="case-1",
        document_id="doc-1",
        chunk_id="chunk-1",
        exact_text="The network expanded in 2025.",
        source_span_reference="p1",
        system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
    )
    retrieval_query = RetrievalQuery(
        query_id="query-1",
        case_id="case-1",
        query_text="claim evidence query",
        requested_k=5,
        retrieval_method="hybrid",
        document_ids=("doc-1",),
    )
    retrieval_result = RetrievalResultSet(
        query_id="query-1",
        case_id="case-1",
        hits=(
            RetrievalHit(
                case_id="case-1",
                document_id="doc-1",
                chunk_id="chunk-1",
                rank=1,
                snippet="supporting evidence",
                score=0.92,
                query_text="claim evidence query",
                retrieval_method="hybrid",
            ),
        ),
        returned_k=1,
        retrieval_method="hybrid",
    )

    request = ClaimVerificationRequest(
        claim=claim,
        retrieval_query=retrieval_query,
        retrieved_evidence=retrieval_result,
    )

    assert request.claim is claim
    assert request.claim.claim_id == "claim-1"
    assert request.retrieval_query is retrieval_query
    assert request.retrieved_evidence is retrieval_result


def test_claim_verification_outcome_keeps_request_and_verification() -> None:
    request = ClaimVerificationRequest(
        claim=Claim(
            claim_id="claim-1",
            case_id="case-1",
            document_id="doc-1",
            chunk_id="chunk-1",
            exact_text="The network expanded in 2025.",
            source_span_reference="p1",
            system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
            rationale=None,
        ),
        retrieval_query=RetrievalQuery(
            query_id="query-1",
            case_id="case-1",
            query_text="claim evidence query",
            requested_k=3,
        ),
        retrieved_evidence=RetrievalResultSet(
            query_id="query-1",
            case_id="case-1",
            hits=(),
        ),
    )
    verification = ClaimVerification(
        claim_id="claim-1",
        case_id="case-1",
        verdict=VerificationVerdict.SUPPORT,
        supporting_chunk_ids=("chunk-1",),
        contradicting_chunk_ids=(),
        analyst_notes="system-supported",
    )

    outcome = ClaimVerificationOutcome(request=request, verification=verification)

    assert outcome.request is request
    assert outcome.verification is verification


def test_application_verification_contracts_are_immutable() -> None:
    request = ClaimVerificationRequest(
        claim=Claim(
            claim_id="claim-1",
            case_id="case-1",
            document_id="doc-1",
            chunk_id="chunk-1",
            exact_text="The network expanded in 2025.",
            source_span_reference="p1",
            system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
            rationale=None,
        ),
        retrieval_query=RetrievalQuery(
            query_id="query-1",
            case_id="case-1",
            query_text="claim evidence query",
            requested_k=3,
        ),
        retrieved_evidence=RetrievalResultSet(
            query_id="query-1",
            case_id="case-1",
            hits=(),
        ),
    )

    with pytest.raises(FrozenInstanceError):
        setattr(request, "claim", None)
