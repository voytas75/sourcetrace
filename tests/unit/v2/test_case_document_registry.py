import pytest

from sourcetrace_v2.adapters.storage.memory import InMemoryCaseDocumentRepository
from sourcetrace_v2.app.services.case_documents import (
    CaseDocumentConflictError,
    CaseNotFoundError,
    register_case,
    register_document,
)
from sourcetrace_v2.core.domain.case_documents import CaseRecord, DocumentRecord


def test_registry_persists_case_and_lists_its_documents_by_document_id() -> None:
    repository = InMemoryCaseDocumentRepository()
    case = CaseRecord(case_id="case-1", title="Migration registry")
    second = DocumentRecord(
        document_id="doc-b",
        case_id=case.case_id,
        source_type="url",
        source_locator="https://example.test/b",
    )
    first = DocumentRecord(
        document_id="doc-a",
        case_id=case.case_id,
        source_type="url",
        source_locator="https://example.test/a",
    )

    assert register_case(case=case, repository=repository) == case
    assert register_document(document=second, repository=repository) == second
    assert register_document(document=first, repository=repository) == first
    assert repository.get_case(case_id=case.case_id) == case
    assert repository.get_document(document_id=first.document_id) == first
    assert repository.list_documents_for_case(case_id=case.case_id) == (first, second)


def test_registry_rejects_document_for_unknown_case_without_persisting_it() -> None:
    repository = InMemoryCaseDocumentRepository()
    document = DocumentRecord(
        document_id="doc-1",
        case_id="missing-case",
        source_type="url",
        source_locator="https://example.test/source",
    )

    with pytest.raises(CaseNotFoundError):
        register_document(document=document, repository=repository)

    assert repository.get_document(document_id=document.document_id) is None


def test_registry_rejects_duplicate_case_and_document_identities() -> None:
    repository = InMemoryCaseDocumentRepository()
    case = CaseRecord(case_id="case-1", title="Unique case")
    document = DocumentRecord(
        document_id="doc-1",
        case_id=case.case_id,
        source_type="url",
        source_locator="https://example.test/source",
    )

    register_case(case=case, repository=repository)
    register_document(document=document, repository=repository)

    with pytest.raises(CaseDocumentConflictError):
        register_case(case=case, repository=repository)
    with pytest.raises(CaseDocumentConflictError):
        register_document(document=document, repository=repository)
