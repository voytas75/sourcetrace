import json

from sourcetrace_v2.app.composition.runtime import build_stubbed_memory_runtime
from sourcetrace_v2.app.services.http_api import handle_get_persisted_execution_request, handle_run_minimal_flow_request
from sourcetrace_v2.app.services.readback import load_persisted_execution_view
from sourcetrace_v2.core.domain.models import ResearchResultArtifact, RunPersistenceMarker
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
    assert payload["persistence"]["completeness"] == "complete"
    assert payload["persistence"]["artifact_present"] is True
    assert payload["persistence"]["marker_present"] is True
    assert payload["persistence"]["marker_state"] == "committed"
    assert payload["artifact"]["present"] is True
    assert payload["compiled_artifact"]["present"] is True
    assert payload["evidence_input"]["candidate_count"] == 3
    assert payload["evidence_input"]["candidates"][0]["provider"] == "stub-search"
    assert payload["selected_evidence"]["selected_count"] == 2
    assert payload["selected_evidence"]["selection_notes"][0] == "selected top 2 ranked retrieval candidates"
    assert payload["selected_evidence"]["dropped_count"] == 1
    assert payload["selected_evidence"]["items"][0]["provider"] == "stub-search"
    assert payload["rollup"]["llm_calls"] == 4
    assert payload["rollup"]["degraded_calls"] == 4
    assert payload["receipts"]["stage_count"] == 10
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

    assert response.status_code == 200
    assert payload["job_id"] == "job-api-http"
    assert payload["run_id"] == "run-api-http"
    assert payload["status"] == "found"
    assert payload["persistence"]["completeness"] == "complete"
    assert payload["persistence"]["artifact_present"] is True
    assert payload["persistence"]["marker_present"] is True
    assert payload["persistence"]["marker_state"] == "committed"
    assert payload["artifact"]["present"] is True
    assert payload["compiled_artifact"]["present"] is True
    assert payload["evidence_input"]["candidate_count"] == 3
    assert payload["selected_evidence"]["selected_count"] == 2
    assert payload["selected_evidence"]["rejected_reasons"][0]["reason"] == "rank_limit"
    assert payload["rollup"]["total_tokens"] == 384
    assert payload["receipts"]["stage_count"] == 10
    assert payload["receipts"]["llm_count"] == 4


def test_get_persisted_execution_http_returns_404_with_absent_persistence_block() -> None:
    runtime = build_stubbed_memory_runtime()

    response = handle_get_persisted_execution_request(
        job_id="job-http-missing",
        run_id="run-http-missing",
        runtime=runtime,
    )
    payload = json.loads(response.body)

    assert response.status_code == 404
    assert payload["status"] == "not_found"
    assert payload["job_id"] == "job-http-missing"
    assert payload["run_id"] == "run-http-missing"
    assert payload["persistence"]["completeness"] == "absent"
    assert payload["persistence"]["artifact_present"] is False
    assert payload["persistence"]["marker_present"] is False
    assert payload["persistence"]["marker_state"] is None
    assert payload["compiled_artifact"]["present"] is False
    assert payload["selected_evidence"]["selected_count"] == 0
    assert payload["selected_evidence"]["selection_notes"][0] == "no retrieval candidates available for promotion"


def test_get_persisted_execution_http_returns_202_with_partial_persistence_block() -> None:
    runtime = build_stubbed_memory_runtime()
    runtime.results.save_result(
        ResearchResultArtifact(job_id="job-http-partial", run_id="run-http-partial", result_text="partial")
    )
    runtime.results.save_run_marker(
        RunPersistenceMarker(job_id="job-http-partial-marker-only", run_id="run-http-partial-marker-only")
    )

    artifact_only_response = handle_get_persisted_execution_request(
        job_id="job-http-partial",
        run_id="run-http-partial",
        runtime=runtime,
    )
    artifact_only_payload = json.loads(artifact_only_response.body)

    assert artifact_only_response.status_code == 202
    assert artifact_only_payload["status"] == "incomplete"
    assert artifact_only_payload["persistence"]["completeness"] == "partial"
    assert artifact_only_payload["persistence"]["artifact_present"] is True
    assert artifact_only_payload["compiled_artifact"]["present"] is False
    assert artifact_only_payload["selected_evidence"]["selected_count"] == 0
    assert artifact_only_payload["persistence"]["marker_present"] is False
    assert artifact_only_payload["persistence"]["marker_state"] is None

    marker_only_response = handle_get_persisted_execution_request(
        job_id="job-http-partial-marker-only",
        run_id="run-http-partial-marker-only",
        runtime=runtime,
    )
    marker_only_payload = json.loads(marker_only_response.body)

    assert marker_only_response.status_code == 202
    assert marker_only_payload["status"] == "incomplete"
    assert marker_only_payload["persistence"]["completeness"] == "partial"
    assert marker_only_payload["persistence"]["artifact_present"] is False
    assert marker_only_payload["persistence"]["marker_present"] is True
    assert marker_only_payload["persistence"]["marker_state"] == "committed"
