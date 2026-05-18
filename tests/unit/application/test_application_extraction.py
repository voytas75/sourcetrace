"""Application claim extraction contract tests."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from sourcetrace.application import (
    ClaimExtractionExecution,
    ClaimExtractionOutcome,
    ClaimExtractionRequest,
    ClaimExtractor,
)
from sourcetrace.application.extraction import (
    ClaimExtractionOutcome as ModuleClaimExtractionOutcome,
)
from sourcetrace.application.extraction import (
    ClaimExtractionRequest as ModuleClaimExtractionRequest,
)
from sourcetrace.application.interfaces import (
    ClaimExtractionExecution as InterfacesClaimExtractionExecution,
)
from sourcetrace.application.interfaces import (
    ClaimExtractor as InterfacesClaimExtractor,
)
from sourcetrace.domain import Claim, ClaimEvidenceLink, Document, DocumentChunk
from sourcetrace.domain.types import VerificationVerdict


def test_application_package_re_exports_claim_extraction_contracts() -> None:
    assert ClaimExtractionRequest is ModuleClaimExtractionRequest
    assert ClaimExtractionOutcome is ModuleClaimExtractionOutcome
    assert ClaimExtractor is InterfacesClaimExtractor
    assert ClaimExtractionExecution is InterfacesClaimExtractionExecution


def test_claim_extraction_execution_bundle_keeps_explicit_callable_dependency() -> None:
    def extract_claims(request: ClaimExtractionRequest) -> ClaimExtractionOutcome:
        document = Document(
            document_id=request.document_id,
            case_id=request.case_id,
            source_type="url",
            source_url="https://example.test/report",
            publisher=None,
            author=None,
            title=None,
            published_at=None,
            retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
            content_hash="sha256:test",
            language=None,
        )
        chunks = (
            DocumentChunk(
                chunk_id=request.chunk_ids[0],
                case_id=request.case_id,
                document_id=request.document_id,
                raw_text="Prepared extraction chunk.",
                start_char=0,
                end_char=25,
                chunk_index=0,
            ),
        )
        claims = (
            Claim(
                claim_id="claim-1",
                case_id=request.case_id,
                document_id=request.document_id,
                chunk_id=request.chunk_ids[0],
                exact_text="The network expanded in 2025.",
                source_span_reference="p1",
                system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
                rationale=None,
            ),
        )
        evidence_links = (
            ClaimEvidenceLink(
                claim_id="claim-1",
                document_id=request.document_id,
                chunk_id=request.chunk_ids[0],
                evidence_rank=1,
                evidence_verdict=VerificationVerdict.SUPPORT,
                rationale="Direct source mention",
                snippet="The network expanded in 2025.",
                score=0.91,
            ),
        )
        return ClaimExtractionOutcome(
            request=request,
            document=document,
            chunks=chunks,
            claims=claims,
            evidence_links=evidence_links,
        )

    execution = ClaimExtractionExecution(extract_claims=extract_claims)

    assert execution.extract_claims is extract_claims


def test_claim_extraction_request_and_outcome_keep_document_chunk_claim_context() -> None:
    request = ClaimExtractionRequest(
        case_id="case-1",
        document_id="doc-1",
        chunk_ids=("chunk-1", "chunk-2"),
        extraction_method="llm-structured-v1",
    )
    document = Document(
        document_id="doc-1",
        case_id="case-1",
        source_type="url",
        source_url="https://example.test/report",
        publisher="Example News",
        author="Analyst",
        title="Network report",
        published_at=datetime(2026, 5, 18, 0, 0, tzinfo=UTC),
        retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
        content_hash="sha256:abc123",
        language="en",
    )
    chunks = (
        DocumentChunk(
            chunk_id="chunk-1",
            case_id="case-1",
            document_id="doc-1",
            raw_text="First evidence paragraph.",
            start_char=0,
            end_char=25,
            chunk_index=0,
            position_reference="p1",
            previous_chunk_id=None,
            next_chunk_id="chunk-2",
        ),
        DocumentChunk(
            chunk_id="chunk-2",
            case_id="case-1",
            document_id="doc-1",
            raw_text="Second evidence paragraph.",
            start_char=26,
            end_char=52,
            chunk_index=1,
            position_reference="p2",
            previous_chunk_id="chunk-1",
            next_chunk_id=None,
        ),
    )
    claims = (
        Claim(
            claim_id="claim-1",
            case_id="case-1",
            document_id="doc-1",
            chunk_id="chunk-1",
            exact_text="The network expanded in 2025.",
            source_span_reference="p1",
            system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
            rationale=None,
        ),
    )
    evidence_links = (
        ClaimEvidenceLink(
            claim_id="claim-1",
            document_id="doc-1",
            chunk_id="chunk-1",
            evidence_rank=1,
            evidence_verdict=VerificationVerdict.SUPPORT,
            rationale="Direct source mention",
            snippet="The network expanded in 2025.",
            score=0.91,
        ),
    )

    outcome = ClaimExtractionOutcome(
        request=request,
        document=document,
        chunks=chunks,
        claims=claims,
        evidence_links=evidence_links,
    )

    assert outcome.request is request
    assert outcome.document is document
    assert outcome.chunks == chunks
    assert outcome.claims == claims
    assert outcome.evidence_links == evidence_links


def test_claim_extraction_contracts_are_immutable() -> None:
    request = ClaimExtractionRequest(
        case_id="case-1",
        document_id="doc-1",
        chunk_ids=("chunk-1",),
    )

    with pytest.raises(FrozenInstanceError):
        setattr(request, "document_id", "doc-2")
