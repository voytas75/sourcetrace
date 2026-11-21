import json
from pathlib import Path
from urllib.parse import urlencode
from wsgiref.util import setup_testing_defaults

import pytest

from sourcetrace_v2.adapters.storage.case_documents_jsonl import JsonlCaseDocumentRepository
from sourcetrace_v2.app.composition.runtime import build_stubbed_memory_runtime
from sourcetrace_v2.app.services.case_documents import register_case, register_document
from sourcetrace_v2.core.domain.case_documents import CaseRecord, DocumentRecord
from sourcetrace_v2.operator import www
from sourcetrace_v2.operator.readback import main


def test_operator_case_documents_after_reopen(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SOURCETRACE_RESEARCH_DATA_DIR", str(tmp_path))

    monkeypatch.setattr(www, "_runtime", build_stubbed_memory_runtime)
    special_id = "żółć/a +%"
    repository = JsonlCaseDocumentRepository(tmp_path)
    for case_id in (special_id, "empty", "other"):
        register_case(case=CaseRecord(case_id, f"Case {case_id}"), repository=repository)
    register_document(document=DocumentRecord("a", special_id, "note", "ref:<A>", "<Title>"), repository=repository)
    register_document(document=DocumentRecord("b", "other", "note", "other-only"), repository=repository)
    del repository
    app = www.build_wsgi_app()

    def read(case_id: str) -> tuple[str, str]:
        statuses: list[str] = []
        environ: dict[str, object] = {}
        setup_testing_defaults(environ)
        environ["PATH_INFO"] = "/cases/documents"
        environ["QUERY_STRING"] = urlencode({"case_id": case_id})

        def start_response(status: str, headers: list[tuple[str, str]], exc_info: object = None):
            statuses.append(status)
            return lambda chunk: None

        body = b"".join(app(environ, start_response)).decode()
        return statuses[0], body

    status, body = read(special_id)
    assert status == "200 OK"
    assert f"Case {special_id}" in body and "&lt;Title&gt;" in body and "ref:&lt;A&gt;" in body
    assert "other-only" not in body
    status, body = read("empty")
    assert status == "200 OK" and "No documents registered" in body
    assert read("missing")[0] == "404 Not Found"
    (tmp_path / "documents.jsonl").write_text("broken\n", encoding="utf-8")
    status, body = read(special_id)
    assert status == "500 Internal Server Error" and "case_document_storage_error" in body


def test_operator_start_fails_before_binding(monkeypatch: pytest.MonkeyPatch) -> None:
    def invalid_runtime() -> None:
        raise RuntimeError("invalid provider configuration")

    def unexpected_bind(*args: object) -> None:
        pytest.fail("Operator must validate configuration before binding")

    monkeypatch.setattr(www, "_runtime", invalid_runtime)
    monkeypatch.setattr(www, "make_server", unexpected_bind)
    with pytest.raises(RuntimeError, match="invalid provider configuration"):
        www.run_server(host="127.0.0.1", port=0)


def test_operator_readback_execution_mode_prints_projected_payload(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(
        "sourcetrace_v2.operator.readback.build_stubbed_jsonl_runtime",
        lambda **kwargs: type("Runtime", (), {"results": object(), "receipts": object()})(),
    )
    monkeypatch.setattr(
        "sourcetrace_v2.operator.readback.load_persisted_execution_view",
        lambda **kwargs: type("View", (), {"status": type("Status", (), {"value": "found"})()})(),
    )
    monkeypatch.setattr(
        "sourcetrace_v2.operator.readback.project_persisted_execution_view",
        lambda **kwargs: {"status": "found", "kind": "execution", "job_id": "job-1", "run_id": "run-1"},
    )

    rc = main(["execution", "job-1", "run-1", "--artifacts-dir", str(tmp_path), "--json-pretty"])

    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 0
    assert payload["kind"] == "execution"
    assert payload["job_id"] == "job-1"


def test_operator_readback_compiled_mode_returns_nonzero_for_missing(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(
        "sourcetrace_v2.operator.readback.build_stubbed_jsonl_runtime",
        lambda **kwargs: type("Runtime", (), {"results": object(), "receipts": object()})(),
    )
    monkeypatch.setattr(
        "sourcetrace_v2.operator.readback.load_persisted_compiled_artifact_view",
        lambda **kwargs: type("View", (), {"status": type("Status", (), {"value": "not_found"})()})(),
    )
    monkeypatch.setattr(
        "sourcetrace_v2.operator.readback.project_persisted_compiled_artifact_view",
        lambda **kwargs: {"status": "not_found", "kind": "compiled", "job_id": "job-1", "run_id": "run-x"},
    )

    rc = main(["compiled", "job-1", "run-x", "--artifacts-dir", str(tmp_path)])

    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 1
    assert payload["kind"] == "compiled"
    assert payload["status"] == "not_found"
