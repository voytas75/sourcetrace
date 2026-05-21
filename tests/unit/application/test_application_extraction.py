"""Application claim extraction contract tests."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from sourcetrace.application import (
    ClaimExtractionExecution,
    ClaimExtractionOutcome,
    ClaimExtractionRequest,
    ClaimExtractor,
    build_llm_claim_extractor,
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
            dropped_claim_items=0,
            dropped_evidence_items=0,
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
    assert outcome.dropped_claim_items == 0
    assert outcome.dropped_evidence_items == 0


def test_claim_extraction_contracts_are_immutable() -> None:
    request = ClaimExtractionRequest(
        case_id="case-1",
        document_id="doc-1",
        chunk_ids=("chunk-1",),
    )

    with pytest.raises(FrozenInstanceError):
        setattr(request, "document_id", "doc-2")


def test_build_llm_claim_extractor_deduplicates_near_duplicate_claims() -> None:
    document = Document(
        document_id="doc-1",
        case_id="case-1",
        source_type="url",
        source_url="https://example.test/climate",
        publisher="Example Climate Desk",
        author="Analyst",
        title="Climate note",
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
            raw_text="Climate analysis chunk.",
            start_char=0,
            end_char=23,
            chunk_index=0,
            position_reference="p1",
        ),
    )

    class _Result:
        payload = {
            "claims": [
                {
                    "claim_id": "claim-1",
                    "exact_text": "Global temperatures in 2025 did not quite reach the heights of 2024.",
                    "chunk_id": "chunk-1",
                    "source_span_reference": "p1",
                },
                {
                    "claim_id": "claim-2",
                    "exact_text": "Global temperatures in 2025 did not quite reach the heights of 2024 partly because of the cooling influence of La Nina.",
                    "chunk_id": "chunk-1",
                    "source_span_reference": "p1",
                },
                {
                    "claim_id": "claim-3",
                    "exact_text": "Researchers warn that short-term variability should not be mistaken for a reversal of the broader warming trend.",
                    "chunk_id": "chunk-1",
                    "source_span_reference": "p1",
                },
            ]
        }

    extractor = build_llm_claim_extractor(extract_claims=lambda _: _Result())

    outcome = extractor(
        ClaimExtractionRequest(
            case_id="case-1",
            document_id="doc-1",
            chunk_ids=("chunk-1",),
            extraction_method="llm-structured-v1",
        ),
        document=document,
        chunks=chunks,
    )

    assert [claim.exact_text for claim in outcome.claims] == [
        "Global temperatures in 2025 did not quite reach the heights of 2024 partly because of the cooling influence of La Nina.",
        "Researchers warn that short-term variability should not be mistaken for a reversal of the broader warming trend.",
    ]


def test_build_llm_claim_extractor_preserves_attribution_when_normalizer_flattens_speaker() -> None:
    document = Document(
        document_id="doc-1",
        case_id="case-1",
        source_type="url",
        source_url="https://example.test/reform",
        publisher="Example Desk",
        author="Reporter",
        title="Reform briefing",
        published_at=datetime(2026, 5, 18, 0, 0, tzinfo=UTC),
        retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
        content_hash="sha256:def456",
        language="en",
    )
    chunks = (
        DocumentChunk(
            chunk_id="chunk-1",
            case_id="case-1",
            document_id="doc-1",
            raw_text="The minister said the reform package is on track, but a watchdog said no dataset has been published yet.",
            start_char=0,
            end_char=107,
            chunk_index=0,
            position_reference="p1",
        ),
    )

    class _Result:
        payload = {
            "claims": [
                {
                    "claim_id": "claim-1",
                    "exact_text": "The minister said the reform package is on track.",
                    "chunk_id": "chunk-1",
                    "source_span_reference": "p1",
                }
            ]
        }

    extractor = build_llm_claim_extractor(
        extract_claims=lambda _: _Result(),
        normalize_claim=lambda text: type("_Normalized", (), {"text": "The reform package is on track."})(),
    )

    outcome = extractor(
        ClaimExtractionRequest(
            case_id="case-1",
            document_id="doc-1",
            chunk_ids=("chunk-1",),
            extraction_method="llm-structured-v1",
        ),
        document=document,
        chunks=chunks,
    )

    assert [claim.exact_text for claim in outcome.claims] == [
        "The minister said the reform package is on track."
    ]


def test_build_llm_claim_extractor_infers_unique_paraphrased_claim_grounding() -> None:
    document = Document(
        document_id="doc-1",
        case_id="case-1",
        source_type="url",
        source_url="https://example.test/housing",
        publisher="Example City Desk",
        author="Reporter",
        title="Housing maintenance briefing",
        published_at=datetime(2026, 5, 18, 0, 0, tzinfo=UTC),
        retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
        content_hash="sha256:mno345",
        language="en",
    )
    chunks = (
        DocumentChunk(
            chunk_id="chunk-1",
            case_id="case-1",
            document_id="doc-1",
            raw_text="The parks department opened two pools after repairs.",
            start_char=0,
            end_char=52,
            chunk_index=0,
            position_reference="p1",
        ),
        DocumentChunk(
            chunk_id="chunk-2",
            case_id="case-1",
            document_id="doc-1",
            raw_text=(
                "The council released a housing maintenance update. "
                "A municipal audit found that 42 elevators failed required safety inspections in April. "
                "Officials said repair contracts will be issued next month, and the report also summarized "
                "staffing levels, budget transfers, tenant notices, emergency work orders, and procurement "
                "delays across five boroughs."
            ),
            start_char=53,
            end_char=418,
            chunk_index=1,
            position_reference="p2",
        ),
    )

    class _Result:
        payload = {
            "claims": [
                {
                    "claim_id": "claim-1",
                    "exact_text": "The city audit found dozens of elevators failed safety inspections in April.",
                }
            ]
        }

    extractor = build_llm_claim_extractor(extract_claims=lambda _: _Result())

    outcome = extractor(
        ClaimExtractionRequest(
            case_id="case-1",
            document_id="doc-1",
            chunk_ids=("chunk-1", "chunk-2"),
            extraction_method="llm-structured-v1",
        ),
        document=document,
        chunks=chunks,
    )

    assert len(outcome.claims) == 1
    assert outcome.claims[0].chunk_id == "chunk-2"
    assert outcome.claims[0].source_span_reference == "p2"
    assert len(outcome.evidence_links) == 1
    assert outcome.evidence_links[0].chunk_id == "chunk-2"
    assert outcome.evidence_links[0].rationale == "Initial extraction link from chunk p2."


def test_build_llm_claim_extractor_filters_helpdesk_style_claim_payloads() -> None:
    document = Document(
        document_id="doc-1",
        case_id="case-1",
        source_type="note",
        source_url=None,
        publisher=None,
        author=None,
        title="Outage note",
        published_at=None,
        retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
        content_hash="sha256:ghi789",
        language="en",
    )
    chunks = (
        DocumentChunk(
            chunk_id="chunk-1",
            case_id="case-1",
            document_id="doc-1",
            raw_text="Power was restored after a substation outage. Around 18000 customers were affected at the peak of the disruption. No injuries were reported.",
            start_char=0,
            end_char=140,
            chunk_index=0,
            position_reference="p1",
        ),
    )

    class _Result:
        payload = {
            "claims": [
                {
                    "claim_id": "claim-1",
                    "exact_text": "Glad to hear power was restored after the substation outage. If you want, I can help you draft an outage update, customer notice, or incident summary.",
                    "chunk_id": "chunk-1",
                    "source_span_reference": "p1",
                },
                {
                    "claim_id": "claim-2",
                    "exact_text": "At the peak of the disruption, around 18,000 customers were affected.",
                    "chunk_id": "chunk-1",
                    "source_span_reference": "p1",
                },
                {
                    "claim_id": "claim-3",
                    "exact_text": "No injuries were reported.",
                    "chunk_id": "chunk-1",
                    "source_span_reference": "p1",
                },
            ]
        }

    extractor = build_llm_claim_extractor(extract_claims=lambda _: _Result())

    outcome = extractor(
        ClaimExtractionRequest(
            case_id="case-1",
            document_id="doc-1",
            chunk_ids=("chunk-1",),
            extraction_method="llm-structured-v1",
        ),
        document=document,
        chunks=chunks,
    )

    assert [claim.exact_text for claim in outcome.claims] == [
        "At the peak of the disruption, around 18,000 customers were affected.",
        "No injuries were reported.",
    ]


def test_build_llm_claim_extractor_filters_helpdesk_style_claim_payload_variants() -> None:
    document = Document(
        document_id="doc-1",
        case_id="case-1",
        source_type="note",
        source_url=None,
        publisher=None,
        author=None,
        title="Outage note",
        published_at=None,
        retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
        content_hash="sha256:jkl012",
        language="en",
    )
    chunks = (
        DocumentChunk(
            chunk_id="chunk-1",
            case_id="case-1",
            document_id="doc-1",
            raw_text="Power was restored after a substation outage. Around 18000 customers were affected at the peak of the disruption. No injuries were reported.",
            start_char=0,
            end_char=140,
            chunk_index=0,
            position_reference="p1",
        ),
    )

    class _Result:
        payload = {
            "claims": [
                {
                    "claim_id": "claim-1",
                    "exact_text": "Glad to hear power was restored after the substation outage. If you want, I can help draft a status update, customer notice, or incident summary.",
                    "chunk_id": "chunk-1",
                    "source_span_reference": "p1",
                },
                {
                    "claim_id": "claim-2",
                    "exact_text": "At the peak of the disruption, around 18,000 customers were affected.",
                    "chunk_id": "chunk-1",
                    "source_span_reference": "p1",
                },
            ]
        }

    extractor = build_llm_claim_extractor(extract_claims=lambda _: _Result())

    outcome = extractor(
        ClaimExtractionRequest(
            case_id="case-1",
            document_id="doc-1",
            chunk_ids=("chunk-1",),
            extraction_method="llm-structured-v1",
        ),
        document=document,
        chunks=chunks,
    )

    assert [claim.exact_text for claim in outcome.claims] == [
        "At the peak of the disruption, around 18,000 customers were affected."
    ]
