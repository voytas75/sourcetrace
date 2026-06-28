from sourcetrace_v2.app.composition.runtime import build_stubbed_memory_runtime
from sourcetrace_v2.app.services.http_api import handle_run_minimal_flow_request
from sourcetrace_v2.app.services.readback import load_persisted_execution_view
from sourcetrace_v2.core.domain.models import ResearchResultArtifact
from sourcetrace_v2.projections.api.readback import project_persisted_execution_view


def test_operator_trust_contract_marks_complete_nonfailed_run_as_weak_when_degraded_only() -> None:
    runtime = build_stubbed_memory_runtime()
    handle_run_minimal_flow_request(
        job_id="job-trust-weak",
        run_id="run-trust-weak",
        seed_text="please use fallback",
        runtime=runtime,
    )

    view = load_persisted_execution_view(
        job_id="job-trust-weak",
        run_id="run-trust-weak",
        results=runtime.results,
        receipts=runtime.receipts,
    )
    payload = project_persisted_execution_view(view=view)

    assert payload["trust"]["status"] == "needs_review"
    assert payload["trust"]["reasons"] == ["degraded_llm_calls", "low_confidence_selected_shape"]


def test_operator_trust_contract_marks_incomplete_persistence_as_degraded() -> None:
    runtime = build_stubbed_memory_runtime()
    runtime.results.save_result(ResearchResultArtifact(job_id="job-trust-inc", run_id="run-trust-inc", result_text="partial"))

    view = load_persisted_execution_view(
        job_id="job-trust-inc",
        run_id="run-trust-inc",
        results=runtime.results,
        receipts=runtime.receipts,
    )
    payload = project_persisted_execution_view(view=view)

    assert payload["trust"]["status"] == "degraded"
    assert payload["trust"]["reasons"] == ["persistence_incomplete"]
