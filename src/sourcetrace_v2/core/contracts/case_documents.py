from __future__ import annotations

from typing import Protocol

from sourcetrace_v2.core.domain.case_documents import CaseRecord, DocumentRecord


class CaseDocumentRepository(Protocol):
    def save_case(self, case: CaseRecord) -> CaseRecord: ...

    def get_case(self, *, case_id: str) -> CaseRecord | None: ...

    def save_document(self, document: DocumentRecord) -> DocumentRecord: ...

    def get_document(self, *, document_id: str) -> DocumentRecord | None: ...

    def list_documents_for_case(
        self, *, case_id: str
    ) -> tuple[DocumentRecord, ...]: ...
