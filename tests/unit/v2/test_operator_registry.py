import json
import subprocess
import sys
from pathlib import Path

import pytest

from sourcetrace_v2.adapters.storage.case_documents_jsonl import (
    JsonlCaseDocumentRepository,
)


def invoke(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "sourcetrace_v2.operator.registry", *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


@pytest.mark.parametrize(
    "args", [(), ("case",), ("document",), ("case", "add"), ("document", "add")]
)
def test_help(*, args: tuple[str, ...]) -> None:
    result = invoke(*args, "--help")
    assert result.returncode == 0 and "usage:" in result.stdout and not result.stderr


def test_registry_round_trip(tmp_path: Path) -> None:
    root = ("--artifacts-dir", str(tmp_path))
    case = ("case", "add", "--case-id", "żółć/a", "--title", "Sprawa")
    document = (
        "document",
        "add",
        "--case-id",
        "żółć/a",
        "--document-id",
        "d",
        "--source-type",
        "note",
        "--source-locator",
        "ref",
    )

    def check(args: tuple[str, ...], status: int, expected: dict[str, object]) -> None:
        result = invoke(*root, *args)
        assert result.returncode == status and not result.stderr
        assert json.loads(result.stdout) == expected

    check(document, 1, {"ok": False, "code": "case_not_found"})
    assert not list(tmp_path.iterdir())
    for args, field, value in (
        (case, "case_id", "żółć/a"),
        (document, "document_id", "d"),
    ):
        result = invoke(*root, *args)
        assert result.returncode == 0 and not result.stderr
        payload = json.loads(result.stdout)
        assert payload["ok"] is True and payload["record"][field] == value
    repo = JsonlCaseDocumentRepository(tmp_path)
    before = repo.case_path.read_bytes(), repo.document_path.read_bytes()
    check(case, 1, {"ok": False, "code": "conflict"})
    check(document, 1, {"ok": False, "code": "conflict"})
    docs = repo.list_documents_for_case(case_id="żółć/a")
    assert [doc.document_id for doc in docs] == ["d"]
    assert before == (repo.case_path.read_bytes(), repo.document_path.read_bytes())
    for corrupt in (b"broken\n", b"[" * 10_000 + b"\n"):
        repo.document_path.write_bytes(corrupt)
        check(document, 1, {"ok": False, "code": "storage_error"})
        assert repo.document_path.read_bytes() == corrupt


def test_invalid_arguments_do_not_write(tmp_path: Path) -> None:
    result = invoke(
        "--artifacts-dir",
        str(tmp_path),
        "case",
        "add",
        "--case-id",
        " ",
        "--title",
        "Title",
    )
    assert result.returncode == 2 and result.stderr and not result.stdout
    assert not list(tmp_path.iterdir())
