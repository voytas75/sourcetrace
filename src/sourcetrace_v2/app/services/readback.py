from __future__ import annotations

from sourcetrace_v2.core.contracts.persistence import ReceiptRepository, ResultArtifactRepository
from sourcetrace_v2.core.contracts.read_models import PersistedExecutionView, PersistedViewStatus
from sourcetrace_v2.execution.rollups.builder import build_execution_rollup


def load_persisted_execution_view(*, job_id: str, run_id: str, results: ResultArtifactRepository, receipts: ReceiptRepository) -> PersistedExecutionView:
    artifact = results.get_result(job_id=job_id, run_id=run_id)
    stage_receipts = receipts.list_stage_receipts(job_id=job_id, run_id=run_id)
    llm_receipts = receipts.list_llm_receipts(job_id=job_id, run_id=run_id)
    rollup = build_execution_rollup(
        job_id=job_id,
        run_id=run_id,
        stage_receipts=stage_receipts,
        llm_receipts=llm_receipts,
    )
    if artifact is None and not stage_receipts and not llm_receipts:
        status = PersistedViewStatus.NOT_FOUND
    elif artifact is None:
        status = PersistedViewStatus.INCOMPLETE
    else:
        status = PersistedViewStatus.FOUND
    return PersistedExecutionView(
        status=status,
        artifact=artifact,
        stage_receipts=stage_receipts,
        llm_receipts=llm_receipts,
        rollup=rollup,
    )
