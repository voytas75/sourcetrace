from pathlib import Path
from typing import cast

import pytest

from sourcetrace_v2.adapters.storage.case_documents_jsonl import (
    CaseDocumentStorageError,
    JsonlCaseDocumentRepository,
)
from sourcetrace_v2.app.services.case_documents import (
    CaseDocumentConflictError,
    CaseNotFoundError,
    register_case,
    register_document,
)
from sourcetrace_v2.core.domain.case_documents import CaseRecord, DocumentRecord


def _case() -> CaseRecord:
    return CaseRecord(case_id="case-1", title="Durable registry")


def _document(*, document_id: str, case_id: str = "case-1") -> DocumentRecord:
    return DocumentRecord(
        document_id=document_id,
        case_id=case_id,
        source_type="url",
        source_locator=f"https://example.test/{document_id}",
    )


def test_jsonl_registry_roundtrips_reopened_case_and_sorted_documents(
    tmp_path: Path,
) -> None:
    repository = JsonlCaseDocumentRepository(tmp_path)
    case = _case()
    register_case(case=case, repository=repository)
    register_document(document=_document(document_id="doc-b"), repository=repository)
    register_document(document=_document(document_id="doc-a"), repository=repository)

    reopened = JsonlCaseDocumentRepository(tmp_path)

    assert reopened.get_case(case_id=case.case_id) == case
    assert reopened.list_documents_for_case(case_id=case.case_id) == (
        _document(document_id="doc-a"),
        _document(document_id="doc-b"),
    )


def test_jsonl_registry_preserves_duplicate_and_parent_guards_after_reopen(
    tmp_path: Path,
) -> None:
    repository = JsonlCaseDocumentRepository(tmp_path)
    case = _case()
    document = _document(document_id="doc-1")
    register_case(case=case, repository=repository)
    register_document(document=document, repository=repository)

    reopened = JsonlCaseDocumentRepository(tmp_path)

    with pytest.raises(CaseDocumentConflictError):
        register_case(case=case, repository=reopened)
    with pytest.raises(CaseDocumentConflictError):
        register_document(document=document, repository=reopened)
    with pytest.raises(CaseNotFoundError):
        register_document(
            document=_document(document_id="doc-missing", case_id="missing-case"),
            repository=reopened,
        )


def test_jsonl_registry_rejects_truncated_tail_instead_of_hiding_identity(
    tmp_path: Path,
) -> None:
    repository = JsonlCaseDocumentRepository(tmp_path)
    register_case(case=_case(), repository=repository)
    repository.case_path.write_text(
        repository.case_path.read_text(encoding="utf-8") + '{"case_id":"partial"\n',
        encoding="utf-8",
    )

    with pytest.raises(CaseDocumentStorageError, match="malformed JSONL record"):
        repository.get_case(case_id="case-1")


def test_jsonl_registry_maps_invalid_case_utf8_to_storage_error(tmp_path: Path) -> None:
    repository = JsonlCaseDocumentRepository(tmp_path)
    repository.case_path.parent.mkdir(parents=True, exist_ok=True)
    repository.case_path.write_bytes(b"\xff")

    with pytest.raises(CaseDocumentStorageError, match="cannot be decoded"):
        repository.get_case(case_id="case-1")


def test_jsonl_registry_maps_invalid_document_utf8_to_storage_error(
    tmp_path: Path,
) -> None:
    repository = JsonlCaseDocumentRepository(tmp_path)
    repository.document_path.parent.mkdir(parents=True, exist_ok=True)
    repository.document_path.write_bytes(b"\xff")

    with pytest.raises(CaseDocumentStorageError, match="cannot be decoded"):
        repository.list_documents_for_case(case_id="case-1")


def test_jsonl_registry_maps_read_io_error_to_storage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = JsonlCaseDocumentRepository(tmp_path)
    repository.case_path.parent.mkdir(parents=True, exist_ok=True)
    repository.case_path.write_text("", encoding="utf-8")

    def raise_read_error(*_args: object, **_kwargs: object) -> str:
        raise OSError("storage unavailable")

    monkeypatch.setattr(Path, "read_text", raise_read_error)

    with pytest.raises(CaseDocumentStorageError, match="cannot be read"):
        repository.get_case(case_id="case-1")


def test_jsonl_registry_maps_exists_io_error_to_storage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = JsonlCaseDocumentRepository(tmp_path)

    def raise_exists_error(*_args: object, **_kwargs: object) -> bool:
        raise OSError("storage unavailable")

    monkeypatch.setattr(Path, "exists", raise_exists_error)

    with pytest.raises(CaseDocumentStorageError, match="cannot be read"):
        repository.get_case(case_id="case-1")


def test_jsonl_registry_maps_mkdir_io_error_to_storage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = JsonlCaseDocumentRepository(tmp_path)

    def raise_mkdir_error(*_args: object, **_kwargs: object) -> None:
        raise OSError("storage unavailable")

    monkeypatch.setattr(Path, "mkdir", raise_mkdir_error)

    with pytest.raises(CaseDocumentStorageError, match="cannot be written"):
        repository.save_case(_case())


def test_jsonl_registry_maps_open_io_error_to_storage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = JsonlCaseDocumentRepository(tmp_path)

    def raise_open_error(*_args: object, **_kwargs: object) -> object:
        raise OSError("storage unavailable")

    monkeypatch.setattr(Path, "open", raise_open_error)

    with pytest.raises(CaseDocumentStorageError, match="cannot be written"):
        repository.save_case(_case())


def test_jsonl_registry_maps_write_io_error_to_storage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = JsonlCaseDocumentRepository(tmp_path)

    class FailingWriteHandle:
        def __enter__(self) -> "FailingWriteHandle":
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

        def write(self, _text: str) -> int:
            raise OSError("storage unavailable")

    def open_with_failing_write(
        *_args: object, **_kwargs: object
    ) -> "FailingWriteHandle":
        return FailingWriteHandle()

    monkeypatch.setattr(Path, "open", open_with_failing_write)

    with pytest.raises(CaseDocumentStorageError, match="cannot be written"):
        repository.save_document(_document(document_id="doc-1"))


def test_jsonl_registry_maps_close_io_error_to_storage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = JsonlCaseDocumentRepository(tmp_path)

    class FailingCloseHandle:
        def __enter__(self) -> "FailingCloseHandle":
            return self

        def __exit__(self, *_args: object) -> bool:
            raise OSError("storage unavailable")

        def write(self, text: str) -> int:
            return len(text)

    def open_with_failing_close(
        *_args: object, **_kwargs: object
    ) -> "FailingCloseHandle":
        return FailingCloseHandle()

    monkeypatch.setattr(Path, "open", open_with_failing_close)

    with pytest.raises(CaseDocumentStorageError, match="cannot be written"):
        repository.save_document(_document(document_id="doc-1"))


@pytest.mark.parametrize("contents", ("\n", " \t\n"))
def test_jsonl_registry_rejects_blank_jsonl_records(
    tmp_path: Path, contents: str
) -> None:
    repository = JsonlCaseDocumentRepository(tmp_path)
    repository.case_path.parent.mkdir(parents=True, exist_ok=True)
    repository.case_path.write_text(contents, encoding="utf-8")

    with pytest.raises(CaseDocumentStorageError, match="blank JSONL record"):
        repository.get_case(case_id="case-1")


@pytest.mark.parametrize("constant", ("NaN", "Infinity", "-Infinity"))
def test_jsonl_registry_rejects_nonstandard_json_constants(
    tmp_path: Path, constant: str
) -> None:
    repository = JsonlCaseDocumentRepository(tmp_path)
    repository.case_path.parent.mkdir(parents=True, exist_ok=True)
    repository.case_path.write_text(
        f'{{"case_id":"case-1","title":"Durable","extra":{constant}}}\n',
        encoding="utf-8",
    )

    with pytest.raises(CaseDocumentStorageError, match="malformed JSONL record"):
        repository.get_case(case_id="case-1")


@pytest.mark.parametrize("separator", ("\u2028", "\u2029"))
def test_jsonl_registry_reopens_metadata_with_unicode_line_separators(
    tmp_path: Path, separator: str
) -> None:
    repository = JsonlCaseDocumentRepository(tmp_path)
    case = CaseRecord(case_id="case-1", title=f"Durable{separator}registry")
    register_case(case=case, repository=repository)

    reopened = JsonlCaseDocumentRepository(tmp_path)

    assert reopened.get_case(case_id=case.case_id) == case


def test_jsonl_registry_rejects_non_object_json_record(tmp_path: Path) -> None:
    repository = JsonlCaseDocumentRepository(tmp_path)
    repository.case_path.parent.mkdir(parents=True, exist_ok=True)
    repository.case_path.write_text("[]\n", encoding="utf-8")

    with pytest.raises(CaseDocumentStorageError, match="non-object JSONL record"):
        repository.get_case(case_id="case-1")


def test_jsonl_registry_maps_nonstandard_write_to_storage_error(tmp_path: Path) -> None:
    repository = JsonlCaseDocumentRepository(tmp_path)
    invalid_case = CaseRecord(
        case_id="case-1",
        title=cast(str, float("nan")),
    )

    with pytest.raises(CaseDocumentStorageError, match="cannot be written"):
        repository.save_case(invalid_case)

    assert not repository.case_path.exists()


def test_jsonl_registry_rejects_missing_terminal_delimiter(tmp_path: Path) -> None:
    repository = JsonlCaseDocumentRepository(tmp_path)
    repository.case_path.parent.mkdir(parents=True, exist_ok=True)
    repository.case_path.write_text(
        '{"case_id":"case-1","title":"Durable"}',
        encoding="utf-8",
    )

    with pytest.raises(CaseDocumentStorageError, match="terminal delimiter"):
        repository.get_case(case_id="case-1")
