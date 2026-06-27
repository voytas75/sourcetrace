from __future__ import annotations

from sourcetrace_v2.adapters.llm.interfaces import LlmTextGateway
from sourcetrace_v2.core.domain.identifiers import StageStatus
from sourcetrace_v2.core.domain.models import LlmExecutionReceipt, StageExecutionReceipt
from sourcetrace_v2.execution.context.models import ExecutionContext
from sourcetrace_v2.execution.receipts.collector import ReceiptCollector
from sourcetrace_v2.execution.stages.base import StageResult


class SimpleLlmStage:
    def __init__(self, *, profile_name: str, llm: LlmTextGateway) -> None:
        self.profile_name = profile_name
        self.llm = llm

    def run(self, *, context: ExecutionContext, collector: ReceiptCollector, input_text: str) -> StageResult:
        collector.append_stage(
            StageExecutionReceipt(
                receipt_id=f"stage:{context.stage_id}:start",
                job_id=context.job_id,
                run_id=context.run_id,
                stage_id=context.stage_id,
                call_site=context.call_site,
                status=StageStatus.STARTED,
                attempt=context.attempt,
                round_number=context.round_number,
            )
        )
        try:
            result = self.llm.generate(profile_name=self.profile_name, prompt=input_text)
        except Exception as exc:
            collector.append_stage(
                StageExecutionReceipt(
                    receipt_id=f"stage:{context.stage_id}:failed",
                    job_id=context.job_id,
                    run_id=context.run_id,
                    stage_id=context.stage_id,
                    call_site=context.call_site,
                    status=StageStatus.FAILED,
                    attempt=context.attempt,
                    round_number=context.round_number,
                    detail=str(exc),
                )
            )
            raise
        collector.append_llm(
            LlmExecutionReceipt(
                receipt_id=f"llm:{context.stage_id}:{self.profile_name}",
                job_id=context.job_id,
                run_id=context.run_id,
                stage_id=context.stage_id,
                call_site=context.call_site,
                profile=self.profile_name,
                provider=result.provider_name or result.provider,
                model=result.model_name or result.model,
                coverage_status=result.coverage_status,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                total_tokens=result.total_tokens,
                finish_reason=result.finish_reason,
                degradation_reason=result.degradation_reason,
            )
        )
        collector.append_stage(
            StageExecutionReceipt(
                receipt_id=f"stage:{context.stage_id}:complete",
                job_id=context.job_id,
                run_id=context.run_id,
                stage_id=context.stage_id,
                call_site=context.call_site,
                status=StageStatus.DEGRADED if result.degradation_reason is not None else StageStatus.COMPLETED,
                attempt=context.attempt,
                round_number=context.round_number,
                degradation_reason=result.degradation_reason,
            )
        )
        return StageResult(output_text=result.text)
