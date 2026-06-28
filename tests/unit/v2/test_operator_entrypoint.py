import json

from sourcetrace_v2.operator.run_minimal_flow import main


from sourcetrace_v2.app.composition.runtime import RuntimeAssembly


class _FakeRuntime(RuntimeAssembly):
    pass


def test_operator_entrypoint_runs_one_bounded_flow_and_prints_json(monkeypatch, capsys, tmp_path) -> None:
    monkeypatch.setattr(
        "sourcetrace_v2.operator.run_minimal_flow.build_env_backed_live_litellm_with_searxng_jsonl_runtime",
        lambda **kwargs: _FakeRuntime(
            config=object(),
            llm=object(),
            search=object(),
            results=object(),
            receipts=object(),
            logger=object(),
            pdf=None,
        ),
    )
    monkeypatch.setattr(
        "sourcetrace_v2.operator.run_minimal_flow.RuntimePdfReadGateway",
        lambda analyzer: object(),
    )
    monkeypatch.setattr(
        "sourcetrace_v2.operator.run_minimal_flow.build_research_pdf_analyzer",
        lambda capability: object(),
    )
    monkeypatch.setattr(
        "sourcetrace_v2.operator.run_minimal_flow.handle_run_minimal_flow_request",
        lambda **kwargs: type("Resp", (), {"status_code": 201, "body": json.dumps({"status": "found", "job_id": kwargs['job_id'], "run_id": kwargs['run_id']})})(),
    )

    rc = main([
        "test query",
        "--job-id", "job-op",
        "--run-id", "run-op",
        "--artifacts-dir", str(tmp_path),
        "--json-pretty",
    ])

    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 0
    assert payload["status"] == "found"
    assert payload["job_id"] == "job-op"
    assert payload["run_id"] == "run-op"
