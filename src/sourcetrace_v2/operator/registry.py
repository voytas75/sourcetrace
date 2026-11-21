from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

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


def _nonblank(value: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError("must not be blank")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sourcetrace-v2-registry",
        description="Register local case and document metadata. Writes JSONL and returns JSON; no network.",
        epilog="Example: %(prog)s --artifacts-dir ./registry case add --case-id c1 --title Example",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--artifacts-dir",
        type=_nonblank,
        required=True,
        help="Explicit JSONL directory",
    )
    kinds = parser.add_subparsers(dest="kind", required=True)
    for kind in ("case", "document"):
        group = kinds.add_parser(
            kind, help=f"Manage {kind} metadata", allow_abbrev=False
        )
        actions = group.add_subparsers(required=True)
        add = actions.add_parser(
            "add",
            help=f"Append a {kind} record",
            description=f"Write one {kind} record to local JSONL and return JSON.",
            allow_abbrev=False,
        )
        add.add_argument(
            "--case-id", required=True, type=_nonblank, help="Exact case identifier"
        )
        add.add_argument(
            "--title",
            required=kind == "case",
            type=_nonblank,
            help=f"{kind.capitalize()} title",
        )
        if kind == "case":
            add.add_argument("--description", help="Optional case description")
        else:
            add.add_argument(
                "--document-id",
                required=True,
                type=_nonblank,
                help="Exact document identifier",
            )
            add.add_argument(
                "--source-type", required=True, type=_nonblank, help="Source category"
            )
            add.add_argument(
                "--source-locator",
                required=True,
                type=_nonblank,
                help="Opaque reference; not accessed",
            )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repository = JsonlCaseDocumentRepository(Path(str(args.artifacts_dir)))
    record: CaseRecord | DocumentRecord
    try:
        if args.kind == "case":
            record = register_case(
                case=CaseRecord(args.case_id, args.title, args.description),
                repository=repository,
            )
        else:
            record = register_document(
                document=DocumentRecord(
                    args.document_id,
                    args.case_id,
                    args.source_type,
                    args.source_locator,
                    args.title,
                ),
                repository=repository,
            )
    except CaseDocumentConflictError:
        code = "conflict"
    except CaseNotFoundError:
        code = "case_not_found"
    except (CaseDocumentStorageError, RecursionError):
        code = "storage_error"
    else:
        print(json.dumps({"ok": True, "record": asdict(record)}))
        return 0
    print(json.dumps({"ok": False, "code": code}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
