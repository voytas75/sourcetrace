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
                        "evidence": [
                            {
                                "chunk_id": "chunk-1",
                                "snippet": "Network expansion noted in the first section.",
                                "rationale": "Primary extraction evidence from paragraph one.",
                                "score": 0.82,
                            },
                            {
                                "chunk_id": "chunk-2",
                                "snippet": "Regional rollout details appear later in the same report.",
                                "rationale": "Secondary cross-reference from paragraph two.",
                                "score": 0.51,
                            },
                        ],
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
    assert tuple(link.claim_id for link in outcome.evidence_links) == (
        "claim-1",
        "claim-1",
        "claim-2",
    )
    assert outcome.evidence_links[0].document_id == "doc-1"
    assert outcome.evidence_links[0].chunk_id == "chunk-1"
    assert outcome.evidence_links[0].evidence_rank == 1
    assert outcome.evidence_links[0].evidence_verdict is VerificationVerdict.INSUFFICIENT_EVIDENCE
    assert outcome.evidence_links[0].rationale == "Primary extraction evidence from paragraph one."
    assert outcome.evidence_links[0].snippet == "Network expansion noted in the first section."
    assert outcome.evidence_links[0].score == 0.82
    assert outcome.evidence_links[1].chunk_id == "chunk-2"
    assert outcome.evidence_links[1].evidence_rank == 2
    assert outcome.evidence_links[1].rationale == "Secondary cross-reference from paragraph two."
    assert outcome.evidence_links[1].snippet == "Regional rollout details appear later in the same report."
    assert outcome.evidence_links[1].score == 0.51
    assert outcome.evidence_links[2].rationale == "Initial extraction link from chunk p2."
    assert outcome.evidence_links[2].snippet == "The rollout reached two regions."
    assert outcome.evidence_links[2].score is None
    assert outcome.dropped_claim_items == 0
    assert outcome.dropped_evidence_items == 0
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


def test_build_llm_claim_extractor_uses_claim_normalization_gateway_when_available() -> None:
    captured_normalization_inputs: list[str] = []

    def extract_claims(prepared_text: str) -> LlmStructuredGenerationResult:
        return LlmStructuredGenerationResult(
            payload={
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "chunk_id": "chunk-1",
                        "exact_text": "  Raw claim text with noise.  ",
                        "source_span_reference": "p1",
                    }
                ]
            },
            model="gpt-4o-mini",
        )

    def normalize_claim(claim_text: str):
        captured_normalization_inputs.append(claim_text)
        return type("_NormalizationResult", (), {"text": "Normalized claim text."})()

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
            raw_text="Raw claim text with noise.",
            start_char=0,
            end_char=27,
            chunk_index=0,
            position_reference="p1",
        ),
    )
    extractor = build_llm_claim_extractor(
        extract_claims=extract_claims,
        normalize_claim=normalize_claim,
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

    assert captured_normalization_inputs == ["Raw claim text with noise."]
    assert outcome.claims[0].exact_text == "Normalized claim text."


def test_build_llm_claim_extractor_accepts_common_claim_payload_aliases() -> None:
    captured_normalization_inputs: list[str] = []

    def extract_claims(prepared_text: str) -> LlmStructuredGenerationResult:
        return LlmStructuredGenerationResult(
            payload={
                "claims": [
                    {
                        "text": "  The network expanded in 2025.  ",
                        "chunk": " chunk-1 ",
                        "span": " p1 ",
                        "evidence_items": [
                            {
                                "chunk": " chunk-1 ",
                                "text": "  Network expansion appears in section one.  ",
                                "reason": "  Direct supporting extraction evidence.  ",
                                "score": 0.82,
                            }
                        ],
                    },
                    {
                        "statement": "The rollout reached two regions.",
                        "source_chunk_id": "chunk-2",
                        "evidence": {
                            "source_chunk_id": "chunk-2",
                            "quote": "The report lists two rollout regions.",
                            "explanation": "Direct evidence quote.",
                        },
                    },
                    {
                        "claim": "Whitespace aliases still normalize.",
                        "span_reference": "p3",
                    },
                ]
            },
            model="gpt-4o-mini",
        )

    def normalize_claim(claim_text: str):
        captured_normalization_inputs.append(claim_text)
        return type("_NormalizationResult", (), {"text": claim_text})()

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
        DocumentChunk(
            chunk_id="chunk-2",
            case_id="case-1",
            document_id="doc-1",
            raw_text="The rollout reached two regions.",
            start_char=30,
            end_char=63,
            chunk_index=1,
            position_reference="p2",
        ),
    )
    extractor = build_llm_claim_extractor(
        extract_claims=extract_claims,
        normalize_claim=normalize_claim,
    )

    outcome = extractor(
        ClaimExtractionRequest(
            case_id="case-1",
            document_id="doc-1",
            chunk_ids=("chunk-1", "chunk-2"),
        ),
        document=document,
        chunks=chunks,
    )

    assert tuple(claim.exact_text for claim in outcome.claims) == (
        "The network expanded in 2025.",
        "The rollout reached two regions.",
        "Whitespace aliases still normalize.",
    )
    assert captured_normalization_inputs == [
        "The network expanded in 2025.",
        "The rollout reached two regions.",
        "Whitespace aliases still normalize.",
    ]
    assert tuple(claim.chunk_id for claim in outcome.claims) == ("chunk-1", "chunk-2", "chunk-1")
    assert tuple(claim.source_span_reference for claim in outcome.claims) == ("p1", "p2", "p3")
    assert tuple(link.chunk_id for link in outcome.evidence_links) == (
        "chunk-1",
        "chunk-2",
        "chunk-1",
    )
    assert outcome.evidence_links[0].snippet == "Network expansion appears in section one."
    assert outcome.evidence_links[0].rationale == "Direct supporting extraction evidence."
    assert outcome.evidence_links[0].score == 0.82
    assert outcome.evidence_links[1].snippet == "The report lists two rollout regions."
    assert outcome.evidence_links[1].rationale == "Direct evidence quote."
    assert outcome.evidence_links[2].snippet == "Whitespace aliases still normalize."
    assert outcome.dropped_claim_items == 0
    assert outcome.dropped_evidence_items == 0


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
    assert claims.list_evidence_links_for_claim("claim-1") == outcome.evidence_links


def test_build_llm_claim_extractor_ignores_invalid_evidence_items_and_keeps_dense_ranks() -> None:
    def extract_claims(prepared_text: str) -> LlmStructuredGenerationResult:
        return LlmStructuredGenerationResult(
            payload={
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "chunk_id": "chunk-1",
                        "exact_text": "The network expanded in 2025.",
                        "source_span_reference": "p1",
                        "evidence": [
                            None,
                            "noise",
                            {},
                            {"score": "0.9"},
                            {
                                "snippet": "The first section describes the network expansion.",
                                "score": 0.82,
                            },
                            {
                                "chunk_id": "chunk-2",
                                "rationale": "Cross-reference from a later paragraph.",
                            },
                        ],
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
            previous_chunk_id=None,
            next_chunk_id="chunk-2",
        ),
        DocumentChunk(
            chunk_id="chunk-2",
            case_id="case-1",
            document_id="doc-1",
            raw_text="Cross-reference paragraph.",
            start_char=30,
            end_char=56,
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
        ),
        document=document,
        chunks=chunks,
    )

    assert len(outcome.evidence_links) == 2
    assert tuple(link.evidence_rank for link in outcome.evidence_links) == (1, 2)
    assert outcome.evidence_links[0].chunk_id == "chunk-1"
    assert outcome.evidence_links[0].snippet == "The first section describes the network expansion."
    assert outcome.evidence_links[0].score == 0.82
    assert outcome.evidence_links[1].chunk_id == "chunk-2"
    assert outcome.evidence_links[1].rationale == "Cross-reference from a later paragraph."
    assert outcome.evidence_links[1].snippet == "The network expanded in 2025."
    assert outcome.evidence_links[1].score is None


def test_build_llm_claim_extractor_falls_back_to_single_link_when_evidence_payload_is_invalid() -> None:
    def extract_claims(prepared_text: str) -> LlmStructuredGenerationResult:
        return LlmStructuredGenerationResult(
            payload={
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "chunk_id": "chunk-1",
                        "exact_text": "The network expanded in 2025.",
                        "source_span_reference": "p1",
                        "evidence": [None, "noise", {}, {"score": "0.9"}],
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

    assert len(outcome.evidence_links) == 1
    assert outcome.evidence_links[0].evidence_rank == 1
    assert outcome.evidence_links[0].chunk_id == "chunk-1"
    assert outcome.evidence_links[0].rationale == "Initial extraction link from chunk p1."
    assert outcome.evidence_links[0].snippet == "The network expanded in 2025."
    assert outcome.evidence_links[0].score is None


def test_build_llm_claim_extractor_ignores_invalid_top_level_claim_items() -> None:
    def extract_claims(prepared_text: str) -> LlmStructuredGenerationResult:
        return LlmStructuredGenerationResult(
            payload={
                "claims": [
                    None,
                    "noise",
                    {},
                    {"evidence": [None, {}, {"score": "0.2"}]},
                    {
                        "chunk_id": "chunk-1",
                        "exact_text": "The network expanded in 2025.",
                        "source_span_reference": "p1",
                    },
                    {
                        "claim_id": "claim-explicit",
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
        ),
        document=document,
        chunks=chunks,
    )

    assert tuple(claim.claim_id for claim in outcome.claims) == ("claim-1", "claim-explicit")
    assert tuple(claim.chunk_id for claim in outcome.claims) == ("chunk-1", "chunk-2")
    assert tuple(link.claim_id for link in outcome.evidence_links) == ("claim-1", "claim-explicit")
    assert outcome.evidence_links[0].snippet == "The network expanded in 2025."
    assert outcome.evidence_links[1].snippet == "The rollout reached two regions."
    assert outcome.dropped_claim_items == 4
    assert outcome.dropped_evidence_items == 0


def test_build_llm_claim_extractor_handles_non_list_claim_payload_as_empty() -> None:
    def extract_claims(prepared_text: str) -> LlmStructuredGenerationResult:
        return LlmStructuredGenerationResult(
            payload={"claims": "noise"},
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

    assert outcome.claims == ()
    assert outcome.evidence_links == ()
    assert outcome.dropped_claim_items == 0
    assert outcome.dropped_evidence_items == 0


def test_build_llm_claim_extractor_reports_dropped_evidence_items() -> None:
    def extract_claims(prepared_text: str) -> LlmStructuredGenerationResult:
        return LlmStructuredGenerationResult(
            payload={
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "chunk_id": "chunk-1",
                        "exact_text": "The network expanded in 2025.",
                        "source_span_reference": "p1",
                        "evidence": [
                            None,
                            {},
                            {"score": "0.9"},
                            {"snippet": "Accepted evidence snippet."},
                        ],
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

    assert len(outcome.evidence_links) == 1
    assert outcome.dropped_claim_items == 0
    assert outcome.dropped_evidence_items == 3


def test_build_llm_claim_extractor_treats_whitespace_only_payload_fields_as_missing() -> None:
    def extract_claims(prepared_text: str) -> LlmStructuredGenerationResult:
        return LlmStructuredGenerationResult(
            payload={
                "claims": [
                    {
                        "claim_id": "   ",
                        "chunk_id": "   ",
                        "exact_text": "   ",
                        "source_span_reference": "   ",
                        "evidence": [
                            {"chunk_id": "   ", "snippet": "   ", "rationale": "   "},
                            {
                                "chunk_id": " chunk-2 ",
                                "snippet": "  Accepted evidence snippet.  ",
                                "rationale": "  Accepted evidence rationale.  ",
                            },
                        ],
                    },
                    {
                        "claim_id": "   ",
                        "chunk_id": "   ",
                        "exact_text": "   ",
                        "source_span_reference": "   ",
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
            previous_chunk_id=None,
            next_chunk_id="chunk-2",
        ),
        DocumentChunk(
            chunk_id="chunk-2",
            case_id="case-1",
            document_id="doc-1",
            raw_text="Accepted evidence chunk.",
            start_char=30,
            end_char=54,
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
        ),
        document=document,
        chunks=chunks,
    )

    assert len(outcome.claims) == 1
    assert outcome.claims[0].claim_id == "claim-1"
    assert outcome.claims[0].chunk_id == "chunk-1"
    assert outcome.claims[0].exact_text == ""
    assert outcome.claims[0].source_span_reference == "chunk-span:unknown"
    assert len(outcome.evidence_links) == 1
    assert outcome.evidence_links[0].chunk_id == "chunk-2"
    assert outcome.evidence_links[0].snippet == "Accepted evidence snippet."
    assert outcome.evidence_links[0].rationale == "Accepted evidence rationale."
    assert outcome.dropped_claim_items == 1
    assert outcome.dropped_evidence_items == 1


def test_build_llm_claim_extractor_drops_conversational_helpdesk_claim_texts() -> None:
    def extract_claims(prepared_text: str) -> LlmStructuredGenerationResult:
        return LlmStructuredGenerationResult(
            payload={
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "chunk_id": "chunk-1",
                        "exact_text": (
                            "Could you please clarify which network you mean? "
                            "If you need help, let me know and I can assist."
                        ),
                    },
                    {
                        "claim_id": "claim-2",
                        "chunk_id": "chunk-1",
                        "exact_text": "The network expanded in 2025.",
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

    assert tuple(claim.exact_text for claim in outcome.claims) == (
        "The network expanded in 2025.",
    )
    assert outcome.dropped_claim_items == 1


def test_build_llm_claim_extractor_falls_back_to_single_request_chunk_span_when_claim_fields_are_blank() -> None:
    def extract_claims(prepared_text: str) -> LlmStructuredGenerationResult:
        return LlmStructuredGenerationResult(
            payload={
                "claims": [
                    {
                        "claim_id": "   ",
                        "chunk_id": "   ",
                        "exact_text": "   ",
                        "source_span_reference": "   ",
                        "evidence": [{"snippet": "Accepted evidence snippet."}],
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
            raw_text="Only chunk in request.",
            start_char=0,
            end_char=22,
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

    assert len(outcome.claims) == 1
    assert outcome.claims[0].chunk_id == "chunk-1"
    assert outcome.claims[0].source_span_reference == "p1"
    assert outcome.evidence_links[0].snippet == "Accepted evidence snippet."
