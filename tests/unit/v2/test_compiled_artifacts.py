import json

from sourcetrace_v2.app.composition.runtime import build_stubbed_memory_runtime
from sourcetrace_v2.app.services.compiled_artifacts import build_compiled_artifact
from sourcetrace_v2.app.services.execution import execute_minimal_research_flow
from sourcetrace_v2.app.services.http_api import handle_run_minimal_flow_request
from sourcetrace_v2.app.services.readback import load_persisted_execution_view
from sourcetrace_v2.projections.api.compiled_artifacts import project_compiled_artifact


def test_build_compiled_artifact_from_run_artifact() -> None:
    runtime = build_stubbed_memory_runtime()
    outcome = execute_minimal_research_flow(
        job_id="job-compiled",
        run_id="run-compiled",
        seed_text="test query",
        llm=runtime.llm,
        search=runtime.search,
        config=runtime.config,
        logger=runtime.logger,
    )

    compiled = build_compiled_artifact(artifact=outcome.artifact)

    assert compiled.artifact_id == "compiled:job-compiled:run-compiled"
    assert compiled.summary.startswith("minimal v2 flow")
    assert len(compiled.selected_evidence) == 2
    assert compiled.selected_evidence[0].provider == "stub-search"


def test_run_persists_compiled_artifact_into_readback() -> None:
    runtime = build_stubbed_memory_runtime()
    handle_run_minimal_flow_request(
        job_id="job-compiled-http",
        run_id="run-compiled-http",
        seed_text="test query",
        runtime=runtime,
    )

    view = load_persisted_execution_view(
        job_id="job-compiled-http",
        run_id="run-compiled-http",
        results=runtime.results,
        receipts=runtime.receipts,
    )
    payload = project_compiled_artifact(artifact=view.compiled_artifact)

    assert payload["present"] is True
    assert payload["artifact_id"] == "compiled:job-compiled-http:run-compiled-http"
    assert len(payload["selected_evidence"]) == 2


def test_run_http_projection_exposes_compiled_artifact_block() -> None:
    runtime = build_stubbed_memory_runtime()
    response = handle_run_minimal_flow_request(
        job_id="job-compiled-payload",
        run_id="run-compiled-payload",
        seed_text="test query",
        runtime=runtime,
    )

    payload = json.loads(response.body)
    assert payload["compiled_artifact"]["present"] is True
    assert payload["compiled_artifact"]["artifact_id"] == "compiled:job-compiled-payload:run-compiled-payload"
    assert len(payload["compiled_artifact"]["selected_evidence"]) == 2
