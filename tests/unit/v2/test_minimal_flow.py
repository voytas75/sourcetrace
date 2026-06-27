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
        search=runtime.search,
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
    assert payload["result"]["summary"].startswith("minimal v2 flow | query=stub:research_fast:")
    assert "top_source=stub-search:Stub result 1" in payload["result"]["summary"]
    assert payload["evidence_input"]["query"].startswith("stub:research_fast:")
    assert payload["evidence_input"]["candidate_count"] == 3
    assert payload["selected_evidence"]["selected_count"] == 2
    assert payload["selected_evidence"]["selection_basis"] == "top_ranked_retrieval_candidates"
    assert payload["selected_evidence"]["selection_notes"][0] == "selected top 2 ranked retrieval candidates"
    assert payload["selected_evidence"]["dropped_count"] == 1
    assert payload["selected_evidence"]["rejected_reasons"][0]["reason"] == "rank_limit"
    assert payload["selected_evidence"]["items"][0]["provider"] == "stub-search"
    assert payload["evidence_input"]["candidates"][0]["provider"] == "stub-search"
    assert payload["rollup"]["llm_calls"] == 4
    assert payload["rollup"]["total_tokens"] == 384
    assert payload["receipts"]["llm"] == 4
    assert payload["receipts"]["stages"] == 10
    assert outcome.artifact.result_text.startswith("stub:")
