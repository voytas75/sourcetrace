from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import NoReturn, cast

from sourcetrace_v2.core.domain.case_documents import CaseRecord, DocumentRecord


class CaseDocumentStorageError(ValueError):
    """Raised when durable case/document metadata cannot be read safely."""


def _reject_nonstandard_json_constant(constant: str) -> NoReturn:
    raise ValueError(f"non-standard JSON constant: {constant}")


def _read_rows(path: Path) -> tuple[dict[str, object], ...]:
    try:
        if not path.exists():
            return ()
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        message = f"JSONL storage cannot be decoded: {path.name}"
        raise CaseDocumentStorageError(message) from exc
    except OSError as exc:
        message = f"JSONL storage cannot be read: {path.name}"
        raise CaseDocumentStorageError(message) from exc

    if not text:
        return ()
    if not text.endswith("\n"):
        raise CaseDocumentStorageError(f"missing terminal delimiter in {path.name}")
    lines = text[:-1].split("\n")

    rows: list[dict[str, object]] = []
    for line_number, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line:
            message = f"blank JSONL record in {path.name} at line {line_number}"
            raise CaseDocumentStorageError(message)
        try:
            payload = json.loads(line, parse_constant=_reject_nonstandard_json_constant)
        except ValueError as exc:
            message = f"malformed JSONL record in {path.name} at line {line_number}"
            raise CaseDocumentStorageError(message) from exc
        if not isinstance(payload, dict):
            message = f"non-object JSONL record in {path.name} at line {line_number}"
            raise CaseDocumentStorageError(message)
        rows.append(
            {
                str(key): value
                for key, value in cast(dict[object, object], payload).items()
            }
        )
    return tuple(rows)


def _required_text(row: dict[str, object], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str):
        raise CaseDocumentStorageError(f"missing text field: {field}")
    return value


def _optional_text(row: dict[str, object], field: str) -> str | None:
    value = row.get(field)
    if value is None or isinstance(value, str):
        return value
    raise CaseDocumentStorageError(f"invalid optional text field: {field}")


def _append_record(path: Path, record: CaseRecord | DocumentRecord) -> None:
    try:
        serialized = json.dumps(asdict(record), ensure_ascii=False, allow_nan=False)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(serialized + "\n")
    except (OSError, ValueError) as exc:
        message = f"JSONL storage cannot be written: {path.name}"
        raise CaseDocumentStorageError(message) from exc


def _case_from_row(row: dict[str, object]) -> CaseRecord:
    return CaseRecord(
        case_id=_required_text(row, "case_id"),
        title=_required_text(row, "title"),
        description=_optional_text(row, "description"),
    )


def _document_from_row(row: dict[str, object]) -> DocumentRecord:
    return DocumentRecord(
        document_id=_required_text(row, "document_id"),
        case_id=_required_text(row, "case_id"),
        source_type=_required_text(row, "source_type"),
        source_locator=_required_text(row, "source_locator"),
        title=_optional_text(row, "title"),
    )


class JsonlCaseDocumentRepository:
    """Append-only, metadata-only durable adapter for the P13a repository contract."""

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.case_path = self.base_dir / "cases.jsonl"
        self.document_path = self.base_dir / "documents.jsonl"

    def save_case(self, case: CaseRecord) -> CaseRecord:
        _append_record(self.case_path, case)
        return case

    def get_case(self, *, case_id: str) -> CaseRecord | None:
        for row in _read_rows(self.case_path):
            case = _case_from_row(row)
            if case.case_id == case_id:
                return case
        return None

    def save_document(self, document: DocumentRecord) -> DocumentRecord:
        _append_record(self.document_path, document)
        return document

    def get_document(self, *, document_id: str) -> DocumentRecord | None:
        for row in _read_rows(self.document_path):
            document = _document_from_row(row)
            if document.document_id == document_id:
                return document
        return None

    def list_documents_for_case(self, *, case_id: str) -> tuple[DocumentRecord, ...]:
        return tuple(
            sorted(
                (
                    document
                    for row in _read_rows(self.document_path)
                    if (document := _document_from_row(row)).case_id == case_id
                ),
                key=lambda document: document.document_id,
            )
        )
