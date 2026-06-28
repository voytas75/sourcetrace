import json

from sourcetrace_v2.operator.readback import main


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
