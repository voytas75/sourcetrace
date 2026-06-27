from sourcetrace_v2.app.composition.runtime import build_stubbed_memory_runtime
from sourcetrace_v2.app.services.http_api import handle_run_minimal_flow_request
from sourcetrace_v2.app.services.readback import load_persisted_execution_view


def test_load_persisted_execution_view_roundtrip() -> None:
    runtime = build_stubbed_memory_runtime()
    handle_run_minimal_flow_request(
        job_id="job-readback",
        run_id="run-readback",
        seed_text="please use fallback",
        runtime=runtime,
    )

    view = load_persisted_execution_view(
        job_id="job-readback",
        run_id="run-readback",
        results=runtime.results,
        receipts=runtime.receipts,
    )

    assert view.artifact is not None
    assert view.artifact.job_id == "job-readback"
    assert view.artifact.run_id == "run-readback"
    assert view.rollup.llm_calls == 4
    assert view.rollup.total_tokens == 384
    assert view.rollup.degraded_calls == 4
    assert len(view.stage_receipts) == 8
    assert len(view.llm_receipts) == 4
