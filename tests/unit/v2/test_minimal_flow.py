from sourcetrace_v2.app.composition.runtime import build_stubbed_memory_runtime
from sourcetrace_v2.app.services.execution import execute_minimal_research_flow
from sourcetrace_v2.projections.api.minimal import project_minimal_result


def test_minimal_flow_emits_result_and_rollup() -> None:
    runtime = build_stubbed_memory_runtime()
    outcome = execute_minimal_research_flow(
        job_id="job-v2-test",
        run_id="run-v2-test",
        seed_text="test query",
        llm=runtime.llm,
        config=runtime.config,
        logger=runtime.logger,
    )

    payload = project_minimal_result(
        job=outcome.job,
        run=outcome.run,
        artifact=outcome.artifact,
        collector=outcome.collector,
    )

    assert payload["job"]["job_id"] == "job-v2-test"
    assert payload["job"]["status"] == "done"
    assert payload["run"]["run_id"] == "run-v2-test"
    assert payload["rollup"]["llm_calls"] == 4
    assert payload["rollup"]["total_tokens"] == 384
    assert payload["receipts"]["llm"] == 4
    assert payload["receipts"]["stages"] == 8
    assert outcome.artifact.result_text.startswith("stub:")
