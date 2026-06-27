from sourcetrace_v2.adapters.storage.memory import InMemoryReceiptRepository, InMemoryResultArtifactRepository
from sourcetrace_v2.app.composition.minimal_flow import run_minimal_flow
from sourcetrace_v2.app.services.api_demo import get_persisted_minimal_flow_payload
from sourcetrace_v2.app.services.readback import load_persisted_execution_view
from sourcetrace_v2.execution.receipts.persisted_collector import PersistedReceiptCollector
from sourcetrace_v2.projections.api.readback import project_persisted_execution_view


def test_project_persisted_execution_view_returns_clean_json_shape() -> None:
    result_repo = InMemoryResultArtifactRepository()
    receipt_repo = InMemoryReceiptRepository()
    job, run, artifact, collector = run_minimal_flow(
        job_id="job-api",
        run_id="run-api",
        seed_text="please use fallback",
    )
    persisted = PersistedReceiptCollector(repository=receipt_repo)
    for receipt in collector.stage_receipts:
        persisted.append_stage(receipt)
    for receipt in collector.llm_receipts:
        persisted.append_llm(receipt)
    result_repo.save_result(artifact)

    view = load_persisted_execution_view(
        job_id=job.job_id,
        run_id=run.run_id,
        results=result_repo,
        receipts=receipt_repo,
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


def test_api_demo_returns_projection_payload() -> None:
    payload = get_persisted_minimal_flow_payload(
        job_id="job-api-demo",
        run_id="run-api-demo",
        seed_text="test query",
    )

    assert payload["job_id"] == "job-api-demo"
    assert payload["run_id"] == "run-api-demo"
    assert payload["job_status"] == "done"
    assert payload["artifact"]["present"] is True
    assert payload["rollup"]["total_tokens"] == 384
    assert payload["receipts"]["stage_count"] == 8
    assert payload["receipts"]["llm_count"] == 4
