from sourcetrace_v2.app.composition.minimal_flow import run_minimal_flow
from sourcetrace_v2.projections.api.minimal import project_minimal_result


def test_minimal_flow_emits_result_and_rollup() -> None:
    job, run, artifact, collector = run_minimal_flow(
        job_id="job-v2-test",
        run_id="run-v2-test",
        seed_text="test query",
    )

    payload = project_minimal_result(job=job, run=run, artifact=artifact, collector=collector)

    assert payload["job"]["job_id"] == "job-v2-test"
    assert payload["job"]["status"] == "done"
    assert payload["run"]["run_id"] == "run-v2-test"
    assert payload["rollup"]["llm_calls"] == 4
    assert payload["rollup"]["total_tokens"] == 384
    assert payload["receipts"]["llm"] == 4
    assert payload["receipts"]["stages"] == 8
    assert artifact.result_text.startswith("stub:")
