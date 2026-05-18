from datetime import UTC, datetime

from sourcetrace.domain import (
    Case,
    Claim,
    ClaimVerification,
    Document,
    DocumentChunk,
)
from sourcetrace.domain.types import VerificationVerdict
from sourcetrace.storage import (
    InMemoryCaseRepository,
    InMemoryClaimRepository,
    InMemoryDocumentRepository,
    create_in_memory_persistence,
)
from sourcetrace.storage.interfaces import CorePersistence
from sourcetrace.storage.memory import (
    InMemoryCaseRepository as MemoryInMemoryCaseRepository,
)
from sourcetrace.storage.memory import (
    InMemoryClaimRepository as MemoryInMemoryClaimRepository,
)
from sourcetrace.storage.memory import (
    InMemoryDocumentRepository as MemoryInMemoryDocumentRepository,
)


def test_storage_package_re_exports_in_memory_runtime_adapters() -> None:
    assert InMemoryCaseRepository is MemoryInMemoryCaseRepository
    assert InMemoryDocumentRepository is MemoryInMemoryDocumentRepository
    assert InMemoryClaimRepository is MemoryInMemoryClaimRepository


def test_create_in_memory_persistence_builds_core_bundle() -> None:
    persistence = create_in_memory_persistence()

    assert isinstance(persistence, CorePersistence)
    assert isinstance(persistence.cases, InMemoryCaseRepository)
    assert isinstance(persistence.documents, InMemoryDocumentRepository)
    assert isinstance(persistence.claims, InMemoryClaimRepository)


def test_in_memory_storage_round_trips_core_runtime_records() -> None:
    persistence = create_in_memory_persistence()
    case = Case(
        case_id="case-1",
        title="Bridge reopening",
        document_ids=("doc-1",),
        claim_ids=("claim-1",),
    )
    document = Document(
        document_id="doc-1",
        case_id="case-1",
        source_type="article",
        source_url="https://example.test/bridge",
        publisher="Example News",
        author=None,
        title="Bridge update",
        published_at=None,
        retrieved_at=datetime(2026, 5, 18, tzinfo=UTC),
        content_hash="hash-1",
        language="en",
    )
    chunks = (
        DocumentChunk(
            chunk_id="chunk-2",
            case_id="case-1",
            document_id="doc-1",
            raw_text="Second bridge update paragraph.",
            start_char=31,
            end_char=62,
            chunk_index=2,
        ),
        DocumentChunk(
            chunk_id="chunk-1",
            case_id="case-1",
            document_id="doc-1",
            raw_text="First bridge update paragraph.",
            start_char=0,
            end_char=30,
            chunk_index=1,
        ),
    )
    claim = Claim(
        claim_id="claim-1",
        case_id="case-1",
        document_id="doc-1",
        chunk_id="chunk-1",
        exact_text="The bridge reopened.",
        source_span_reference="p1",
        system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
    )
    verification = ClaimVerification(
        claim_id="claim-1",
        case_id="case-1",
        verdict=VerificationVerdict.SUPPORT,
        supporting_chunk_ids=("chunk-1",),
    )

    persistence.cases.save_case(case)
    persistence.documents.save_document(document)
    persistence.documents.save_chunks(chunks)
    persistence.claims.save_claims((claim,))
    persistence.claims.save_verification(verification)

    assert persistence.cases.get_case("case-1") is case
    assert persistence.documents.get_document("doc-1") is document
    assert tuple(
        chunk.chunk_id
        for chunk in persistence.documents.list_chunks_for_document("case-1", "doc-1")
    ) == ("chunk-1", "chunk-2")
    assert persistence.claims.get_claim("claim-1") is claim
    assert persistence.claims.list_claims_for_case("case-1") == (claim,)
    assert persistence.claims.get_verification("claim-1") is verification
