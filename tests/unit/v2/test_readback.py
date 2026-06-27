from sourcetrace_v2.adapters.storage.memory import InMemoryReceiptRepository, InMemoryResultArtifactRepository
from sourcetrace_v2.app.composition.minimal_flow import run_minimal_flow
from sourcetrace_v2.app.services.persistence_demo import run_persisted_minimal_flow
from sourcetrace_v2.app.services.readback import load_persisted_execution_view
from sourcetrace_v2.execution.receipts.persisted_collector import PersistedReceiptCollector


def test_load_persisted_execution_view_roundtrip() -> None:
    result_repo = InMemoryResultArtifactRepository()
    receipt_repo = InMemoryReceiptRepository()
    job, run, artifact, collector = run_minimal_flow(
        job_id="job-readback",
        run_id="run-readback",
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

    assert view.artifact is not None
    assert view.artifact.job_id == "job-readback"
    assert view.artifact.run_id == "run-readback"
    assert view.rollup.llm_calls == 4
    assert view.rollup.total_tokens == 384
    assert view.rollup.degraded_calls == 4
    assert len(view.stage_receipts) == 8
    assert len(view.llm_receipts) == 4


def test_run_persisted_minimal_flow_returns_readback_summary() -> None:
    payload = run_persisted_minimal_flow(
        job_id="job-demo",
        run_id="run-demo",
        seed_text="test query",
    )

    assert payload["job_id"] == "job-demo"
    assert payload["run_id"] == "run-demo"
    assert payload["job_status"] == "done"
    assert payload["llm_calls"] == 4
    assert payload["total_tokens"] == 384
    assert payload["stage_receipts"] == 8
    assert payload["llm_receipts"] == 4
