import json

from sourcetrace_v2.app.composition.runtime import build_stubbed_memory_runtime
from sourcetrace_v2.app.services.http_api import handle_get_persisted_execution_request, handle_run_minimal_flow_request
from sourcetrace_v2.app.services.readback import load_persisted_execution_view
from sourcetrace_v2.projections.api.readback import project_persisted_execution_view


def test_project_persisted_execution_view_returns_clean_json_shape() -> None:
    runtime = build_stubbed_memory_runtime()
    handle_run_minimal_flow_request(
        job_id="job-api",
        run_id="run-api",
        seed_text="please use fallback",
        runtime=runtime,
    )

    view = load_persisted_execution_view(
        job_id="job-api",
        run_id="run-api",
        results=runtime.results,
        receipts=runtime.receipts,
    )
    payload = project_persisted_execution_view(view=view)

    assert payload["job_id"] == "job-api"
    assert payload["run_id"] == "run-api"
    assert payload["artifact"]["present"] is True
    assert payload["rollup"]["llm_calls"] == 4
    assert payload["rollup"]["degraded_calls"] == 4
    assert payload["receipts"]["stage_count"] == 8
    assert payload["receipts"]["llm_count"] == 4
    assert payload["receipts"]["stages"][0]["stage_id"] == "planning"
    assert payload["receipts"]["llm"][0]["profile"] == "planning_default"


def test_run_then_get_http_path_returns_projection_payload() -> None:
    runtime = build_stubbed_memory_runtime()
    handle_run_minimal_flow_request(
        job_id="job-api-http",
        run_id="run-api-http",
        seed_text="test query",
        runtime=runtime,
    )

    response = handle_get_persisted_execution_request(
        job_id="job-api-http",
        run_id="run-api-http",
        runtime=runtime,
    )
    payload = json.loads(response.body)

    assert payload["job_id"] == "job-api-http"
    assert payload["run_id"] == "run-api-http"
    assert payload["status"] == "found"
    assert payload["artifact"]["present"] is True
    assert payload["rollup"]["total_tokens"] == 384
    assert payload["receipts"]["stage_count"] == 8
    assert payload["receipts"]["llm_count"] == 4
