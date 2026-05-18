"""Application extraction runtime integration tests."""

from datetime import UTC, datetime

from sourcetrace.application.extraction_runtime import build_llm_claim_extractor
from sourcetrace.application.extraction import ClaimExtractionRequest
from sourcetrace.domain import Document, DocumentChunk
from sourcetrace.domain.types import VerificationVerdict
from sourcetrace.llm import LlmStructuredGenerationResult
from sourcetrace.storage import InMemoryClaimRepository


def test_build_llm_claim_extractor_maps_gateway_payload_to_application_outcome() -> None:
    captured_text: str | None = None

    def extract_claims(prepared_text: str) -> LlmStructuredGenerationResult:
        nonlocal captured_text
        captured_text = prepared_text
        return LlmStructuredGenerationResult(
            payload={
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "chunk_id": "chunk-1",
                        "exact_text": "The network expanded in 2025.",
                        "source_span_reference": "p1",
                    },
                    {
                        "claim_id": "claim-2",
                        "chunk_id": "chunk-2",
                        "exact_text": "The rollout reached two regions.",
                        "source_span_reference": "p2",
                    },
                ]
            },
            model="gpt-4o-mini",
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
            raw_text="The network expanded in 2025.",
            start_char=0,
            end_char=29,
            chunk_index=0,
            position_reference="p1",
            previous_chunk_id=None,
            next_chunk_id="chunk-2",
        ),
        DocumentChunk(
            chunk_id="chunk-2",
            case_id="case-1",
            document_id="doc-1",
            raw_text="The rollout reached two regions.",
            start_char=30,
            end_char=63,
            chunk_index=1,
            position_reference="p2",
            previous_chunk_id="chunk-1",
            next_chunk_id=None,
        ),
    )
    extractor = build_llm_claim_extractor(extract_claims=extract_claims)

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

    assert captured_text == (
        "[chunk-1] The network expanded in 2025.\n\n"
        "[chunk-2] The rollout reached two regions."
    )
    assert tuple(claim.claim_id for claim in outcome.claims) == ("claim-1", "claim-2")
    assert outcome.claims[0].chunk_id == "chunk-1"
    assert outcome.claims[0].system_verdict is VerificationVerdict.INSUFFICIENT_EVIDENCE
    assert outcome.evidence_links == ()
    assert outcome.document is document
    assert outcome.chunks == chunks


def test_build_llm_claim_extractor_falls_back_to_chunk_position_reference_when_span_missing() -> None:
    def extract_claims(prepared_text: str) -> LlmStructuredGenerationResult:
        return LlmStructuredGenerationResult(
            payload={
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "chunk_id": "chunk-1",
                        "exact_text": "The network expanded in 2025.",
                    }
                ]
            },
            model="gpt-4o-mini",
        )

    document = Document(
        document_id="doc-1",
        case_id="case-1",
        source_type="url",
        source_url="https://example.test/report",
        publisher=None,
        author=None,
        title=None,
        published_at=None,
        retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
        content_hash="sha256:abc123",
        language=None,
    )
    chunks = (
        DocumentChunk(
            chunk_id="chunk-1",
            case_id="case-1",
            document_id="doc-1",
            raw_text="The network expanded in 2025.",
            start_char=0,
            end_char=29,
            chunk_index=0,
            position_reference="p1",
        ),
    )
    extractor = build_llm_claim_extractor(extract_claims=extract_claims)

    outcome = extractor(
        ClaimExtractionRequest(
            case_id="case-1",
            document_id="doc-1",
            chunk_ids=("chunk-1",),
        ),
        document=document,
        chunks=chunks,
    )

    assert outcome.claims[0].source_span_reference == "p1"


def test_build_llm_claim_extractor_persists_extracted_claims_when_repository_is_provided() -> None:
    def extract_claims(prepared_text: str) -> LlmStructuredGenerationResult:
        return LlmStructuredGenerationResult(
            payload={
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "chunk_id": "chunk-1",
                        "exact_text": "The network expanded in 2025.",
                        "source_span_reference": "p1",
                    }
                ]
            },
            model="gpt-4o-mini",
        )

    document = Document(
        document_id="doc-1",
        case_id="case-1",
        source_type="url",
        source_url="https://example.test/report",
        publisher=None,
        author=None,
        title=None,
        published_at=None,
        retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
        content_hash="sha256:abc123",
        language=None,
    )
    chunks = (
        DocumentChunk(
            chunk_id="chunk-1",
            case_id="case-1",
            document_id="doc-1",
            raw_text="The network expanded in 2025.",
            start_char=0,
            end_char=29,
            chunk_index=0,
            position_reference="p1",
        ),
    )
    claims = InMemoryClaimRepository()
    extractor = build_llm_claim_extractor(
        extract_claims=extract_claims,
        claim_repository=claims,
    )

    outcome = extractor(
        ClaimExtractionRequest(
            case_id="case-1",
            document_id="doc-1",
            chunk_ids=("chunk-1",),
        ),
        document=document,
        chunks=chunks,
    )

    assert claims.list_claims_for_case("case-1") == outcome.claims
