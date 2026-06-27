from __future__ import annotations

from sourcetrace_v2.core.domain.identifiers import StageStatus
from sourcetrace_v2.core.domain.models import ExecutionRollup, LlmExecutionReceipt, StageExecutionReceipt


def build_execution_rollup(*, job_id: str, run_id: str, stage_receipts: tuple[StageExecutionReceipt, ...] | list[StageExecutionReceipt], llm_receipts: tuple[LlmExecutionReceipt, ...] | list[LlmExecutionReceipt]) -> ExecutionRollup:
    return ExecutionRollup(
        job_id=job_id,
        run_id=run_id,
        llm_calls=len(llm_receipts),
        input_tokens=sum(receipt.input_tokens or 0 for receipt in llm_receipts),
        output_tokens=sum(receipt.output_tokens or 0 for receipt in llm_receipts),
        total_tokens=sum(receipt.total_tokens or 0 for receipt in llm_receipts),
        degraded_calls=sum(1 for receipt in llm_receipts if receipt.degradation_reason is not None),
        failed_stages=sum(1 for receipt in stage_receipts if receipt.status is StageStatus.FAILED),
    )
