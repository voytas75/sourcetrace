from sourcetrace_v2.adapters.storage.memory import InMemoryReceiptRepository, InMemoryResultArtifactRepository
from sourcetrace_v2.core.domain.identifiers import StageId, StageStatus
from sourcetrace_v2.core.domain.models import LlmExecutionReceipt, ResearchResultArtifact, StageExecutionReceipt
from sourcetrace_v2.execution.receipts.persisted_collector import PersistedReceiptCollector


def test_in_memory_result_repository_roundtrip() -> None:
    repo = InMemoryResultArtifactRepository()
    artifact = ResearchResultArtifact(job_id="job-1", run_id="run-1", result_text="hello")

    repo.save_result(artifact)

    assert repo.get_result(job_id="job-1", run_id="run-1") == artifact
    assert repo.get_result(job_id="job-1", run_id="run-2") is None


def test_persisted_receipt_collector_stores_receipts() -> None:
    repo = InMemoryReceiptRepository()
    collector = PersistedReceiptCollector(repository=repo)

    collector.append_stage(
        StageExecutionReceipt(
            receipt_id="stage-1",
            job_id="job-1",
            run_id="run-1",
            stage_id=StageId.PLANNING,
            call_site="test",
            status=StageStatus.STARTED,
        )
    )
    collector.append_llm(
        LlmExecutionReceipt(
            receipt_id="llm-1",
            job_id="job-1",
            run_id="run-1",
            stage_id=StageId.PLANNING,
            call_site="test",
            profile="planning_default",
            provider="azure",
            model="gpt-5.4",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
        )
    )

    assert len(repo.list_stage_receipts(job_id="job-1", run_id="run-1")) == 1
    assert len(repo.list_llm_receipts(job_id="job-1", run_id="run-1")) == 1
    assert len(repo.list_stage_receipts(job_id="job-1", run_id="run-2")) == 0
    assert len(repo.list_llm_receipts(job_id="job-1", run_id="run-2")) == 0

    rollup = collector.build_rollup(job_id="job-1", run_id="run-1")
    assert rollup.total_tokens == 30
    assert rollup.llm_calls == 1
