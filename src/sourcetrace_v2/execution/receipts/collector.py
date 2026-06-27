from __future__ import annotations

from dataclasses import dataclass, field

from sourcetrace_v2.core.domain.models import ExecutionRollup, LlmExecutionReceipt, StageExecutionReceipt
from sourcetrace_v2.execution.rollups.builder import build_execution_rollup


@dataclass
class ReceiptCollector:
    stage_receipts: list[StageExecutionReceipt] = field(default_factory=list)
    llm_receipts: list[LlmExecutionReceipt] = field(default_factory=list)

    def append_stage(self, receipt: StageExecutionReceipt) -> None:
        self.stage_receipts.append(receipt)

    def append_llm(self, receipt: LlmExecutionReceipt) -> None:
        self.llm_receipts.append(receipt)

    def build_rollup(self, *, job_id: str, run_id: str) -> ExecutionRollup:
        return build_execution_rollup(
            job_id=job_id,
            run_id=run_id,
            stage_receipts=self.stage_receipts,
            llm_receipts=self.llm_receipts,
        )
