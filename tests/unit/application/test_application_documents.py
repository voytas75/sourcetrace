"""Application document preparation contract tests."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from sourcetrace.application import (
    DocumentPreparationExecution,
    DocumentPreparationOutcome,
    DocumentPreparationRequest,
    DocumentPreparer,
)
from sourcetrace.application.documents import (
    DocumentPreparationOutcome as ModuleDocumentPreparationOutcome,
)
from sourcetrace.application.documents import (
    DocumentPreparationRequest as ModuleDocumentPreparationRequest,
)
from sourcetrace.application.interfaces import (
    DocumentPreparationExecution as InterfacesDocumentPreparationExecution,
)
from sourcetrace.application.interfaces import (
    DocumentPreparer as InterfacesDocumentPreparer,
)
from sourcetrace.domain import Document, DocumentChunk


def test_application_package_re_exports_document_preparation_contracts() -> None:
    assert DocumentPreparationRequest is ModuleDocumentPreparationRequest
    assert DocumentPreparationOutcome is ModuleDocumentPreparationOutcome
    assert DocumentPreparer is InterfacesDocumentPreparer
    assert DocumentPreparationExecution is InterfacesDocumentPreparationExecution


def test_document_preparation_execution_bundle_keeps_explicit_callable_dependency() -> None:
    def prepare_document(
        request: DocumentPreparationRequest,
    ) -> DocumentPreparationOutcome:
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
                chunk_id="chunk-1",
                case_id=request.case_id,
                document_id=request.document_id,
                raw_text="Prepared evidence chunk.",
                start_char=0,
                end_char=24,
                chunk_index=0,
            ),
        )
        return DocumentPreparationOutcome(
            request=request,
            document=document,
            chunks=chunks,
        )

    execution = DocumentPreparationExecution(prepare_document=prepare_document)

    assert execution.prepare_document is prepare_document


def test_document_preparation_request_and_outcome_keep_document_and_chunks() -> None:
    request = DocumentPreparationRequest(
        case_id="case-1",
        document_id="doc-1",
        chunking_method="paragraph-v1",
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

    outcome = DocumentPreparationOutcome(
        request=request,
        document=document,
        chunks=chunks,
    )

    assert outcome.request is request
    assert outcome.document is document
    assert outcome.chunks == chunks


def test_document_preparation_contracts_are_immutable() -> None:
    request = DocumentPreparationRequest(
        case_id="case-1",
        document_id="doc-1",
    )

    with pytest.raises(FrozenInstanceError):
        setattr(request, "document_id", "doc-2")
