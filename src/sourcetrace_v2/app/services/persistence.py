from __future__ import annotations

from sourcetrace_v2.core.contracts.persistence import ReceiptRepository, ResultArtifactRepository
from sourcetrace_v2.core.domain.models import RunPersistenceMarker
from sourcetrace_v2.execution.receipts.persisted_collector import PersistedReceiptCollector
from sourcetrace_v2.app.services.execution import ExecutionOutcome


def persist_execution_outcome(*, outcome: ExecutionOutcome, results: ResultArtifactRepository, receipts: ReceiptRepository) -> None:
    persisted = PersistedReceiptCollector(repository=receipts)
    for receipt in outcome.collector.stage_receipts:
        persisted.append_stage(receipt)
    for receipt in outcome.collector.llm_receipts:
        persisted.append_llm(receipt)
    if outcome.artifact is not None:
        results.save_result(outcome.artifact)
    results.save_run_marker(
        RunPersistenceMarker(job_id=outcome.run.job_id, run_id=outcome.run.run_id)
    )
