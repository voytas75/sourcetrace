import json

from sourcetrace_v2.app.composition.runtime import build_stubbed_memory_runtime
from sourcetrace_v2.app.services.http_api import handle_get_persisted_execution_request, handle_run_minimal_flow_request


def test_handle_run_minimal_flow_request_returns_created_json_response() -> None:
    runtime = build_stubbed_memory_runtime()

    response = handle_run_minimal_flow_request(
        job_id="job-http-run",
        run_id="run-http-run",
        seed_text="test query",
        runtime=runtime,
    )

    payload = json.loads(response.body)
    assert response.status_code == 201
    assert response.content_type.startswith("application/json")
    assert payload["job_id"] == "job-http-run"
    assert payload["run_id"] == "run-http-run"
    assert payload["status"] == "found"
    assert payload["artifact"]["present"] is True
    assert payload["evidence_input"]["candidate_count"] == 3
    assert payload["selected_evidence"]["selected_count"] == 2
    assert payload["rollup"]["total_tokens"] == 384


def test_handle_get_persisted_execution_request_returns_projection() -> None:
    runtime = build_stubbed_memory_runtime()
    handle_run_minimal_flow_request(
        job_id="job-http-get",
        run_id="run-http-get",
        seed_text="please use fallback",
        runtime=runtime,
    )

    response = handle_get_persisted_execution_request(
        job_id="job-http-get",
        run_id="run-http-get",
        runtime=runtime,
    )

    payload = json.loads(response.body)
    assert response.status_code == 200
    assert payload["status"] == "found"
    assert payload["job_id"] == "job-http-get"
    assert payload["run_id"] == "run-http-get"
    assert payload["artifact"]["present"] is True
    assert payload["evidence_input"]["candidate_count"] == 3
    assert payload["selected_evidence"]["selected_count"] == 2
    assert payload["rollup"]["degraded_calls"] == 4


def test_handle_get_persisted_execution_request_returns_not_found() -> None:
    runtime = build_stubbed_memory_runtime()

    response = handle_get_persisted_execution_request(
        job_id="missing-job",
        run_id="missing-run",
        runtime=runtime,
    )

    payload = json.loads(response.body)
    assert response.status_code == 404
    assert payload["status"] == "not_found"
    assert payload["artifact"]["present"] is False
    assert payload["selected_evidence"]["selected_count"] == 0


def test_handle_get_persisted_execution_request_returns_incomplete() -> None:
    runtime = build_stubbed_memory_runtime()
    response = handle_run_minimal_flow_request(
        job_id="job-http-incomplete",
        run_id="run-http-incomplete",
        seed_text="test query",
        runtime=runtime,
    )
    payload = json.loads(response.body)
    runtime.results.artifacts.pop((payload["job_id"], payload["run_id"]))

    response = handle_get_persisted_execution_request(
        job_id="job-http-incomplete",
        run_id="run-http-incomplete",
        runtime=runtime,
    )

    payload = json.loads(response.body)
    assert response.status_code == 202
    assert payload["status"] == "incomplete"
    assert payload["artifact"]["present"] is False
    assert payload["selected_evidence"]["selected_count"] == 0
    assert payload["receipts"]["llm_count"] == 4
