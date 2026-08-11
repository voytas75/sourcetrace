from __future__ import annotations

from sourcetrace_v2.core.contracts.case_documents import CaseDocumentRepository
from sourcetrace_v2.core.domain.case_documents import CaseRecord, DocumentRecord


class CaseDocumentConflictError(Exception):
    """Raised when a case or document identity already exists."""


class CaseNotFoundError(Exception):
    """Raised when a document references an unknown case."""


def register_case(
    *, case: CaseRecord, repository: CaseDocumentRepository
) -> CaseRecord:
    if repository.get_case(case_id=case.case_id) is not None:
        raise CaseDocumentConflictError(f"case identity already exists: {case.case_id}")
    return repository.save_case(case)


def register_document(
    *, document: DocumentRecord, repository: CaseDocumentRepository
) -> DocumentRecord:
    if repository.get_case(case_id=document.case_id) is None:
        raise CaseNotFoundError(f"case identity does not exist: {document.case_id}")
    if repository.get_document(document_id=document.document_id) is not None:
        raise CaseDocumentConflictError(
            f"document identity already exists: {document.document_id}"
        )
    return repository.save_document(document)
