import json

from sourcetrace_v2.app.composition.runtime import build_stubbed_memory_runtime
from sourcetrace_v2.app.services.compiled_readback import load_persisted_compiled_artifact_view
from sourcetrace_v2.app.services.http_api import (
    handle_get_persisted_compiled_artifact_request,
    handle_run_minimal_flow_request,
)
from sourcetrace_v2.core.contracts.compiled_artifacts import CompiledResearchArtifact
from sourcetrace_v2.core.domain.models import ResearchResultArtifact, RunPersistenceMarker
from sourcetrace_v2.projections.api.compiled_readback import project_persisted_compiled_artifact_view


def test_project_persisted_compiled_artifact_view_returns_found_shape() -> None:
    runtime = build_stubbed_memory_runtime()
    handle_run_minimal_flow_request(
        job_id="job-compiled-readback",
        run_id="run-compiled-readback",
        seed_text="test query",
        runtime=runtime,
    )

    view = load_persisted_compiled_artifact_view(
        job_id="job-compiled-readback",
        run_id="run-compiled-readback",
        results=runtime.results,
    )
    payload = project_persisted_compiled_artifact_view(view=view)

    assert payload["status"] == "found"
    assert payload["persistence"]["completeness"] == "complete"
    assert payload["persistence"]["compiled_artifact_present"] is True
    assert payload["compiled_artifact"]["present"] is True


def test_compiled_artifact_http_returns_404_when_absent() -> None:
    runtime = build_stubbed_memory_runtime()

    response = handle_get_persisted_compiled_artifact_request(
        job_id="missing-job",
        run_id="missing-run",
        runtime=runtime,
    )
    payload = json.loads(response.body)

    assert response.status_code == 404
    assert payload["status"] == "not_found"
    assert payload["compiled_artifact"]["present"] is False


def test_compiled_artifact_http_returns_202_for_partial_paths() -> None:
    runtime = build_stubbed_memory_runtime()
    runtime.results.save_compiled_artifact(
        CompiledResearchArtifact(
            artifact_id="compiled:job-partial:run-partial",
            job_id="job-partial",
            run_id="run-partial",
            summary="partial compiled",
        )
    )
    runtime.results.save_run_marker(
        RunPersistenceMarker(job_id="job-marker-only", run_id="run-marker-only")
    )
    runtime.results.save_result(
        ResearchResultArtifact(job_id="job-result-only", run_id="run-result-only", result_text="result only")
    )

    compiled_only = handle_get_persisted_compiled_artifact_request(
        job_id="job-partial",
        run_id="run-partial",
        runtime=runtime,
    )
    compiled_only_payload = json.loads(compiled_only.body)
    assert compiled_only.status_code == 202
    assert compiled_only_payload["status"] == "incomplete"
    assert compiled_only_payload["persistence"]["compiled_artifact_present"] is True
    assert compiled_only_payload["persistence"]["run_artifact_present"] is False

    marker_only = handle_get_persisted_compiled_artifact_request(
        job_id="job-marker-only",
        run_id="run-marker-only",
        runtime=runtime,
    )
    marker_only_payload = json.loads(marker_only.body)
    assert marker_only.status_code == 202
    assert marker_only_payload["status"] == "incomplete"
    assert marker_only_payload["persistence"]["compiled_artifact_present"] is False
    assert marker_only_payload["persistence"]["marker_present"] is True

    result_only = handle_get_persisted_compiled_artifact_request(
        job_id="job-result-only",
        run_id="run-result-only",
        runtime=runtime,
    )
    result_only_payload = json.loads(result_only.body)
    assert result_only.status_code == 202
    assert result_only_payload["status"] == "incomplete"
    assert result_only_payload["persistence"]["compiled_artifact_present"] is False
    assert result_only_payload["persistence"]["run_artifact_present"] is True
