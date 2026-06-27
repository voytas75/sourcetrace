from __future__ import annotations

from dataclasses import dataclass

from sourcetrace_v2.adapters.search.interfaces import SearchGateway
from sourcetrace_v2.core.domain.identifiers import StageStatus
from sourcetrace_v2.core.domain.models import RetrievedEvidenceCandidate, StageExecutionReceipt
from sourcetrace_v2.execution.context.models import ExecutionContext
from sourcetrace_v2.execution.receipts.collector import ReceiptCollector


@dataclass(frozen=True)
class RetrievalStageResult:
    retrieval_query: str
    candidates: tuple[RetrievedEvidenceCandidate, ...]


class RetrievalStage:
    def __init__(self, *, search: SearchGateway, limit: int = 3) -> None:
        self.search = search
        self.limit = limit

    def run(self, *, context: ExecutionContext, collector: ReceiptCollector, input_text: str) -> RetrievalStageResult:
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
            candidates = self.search.search(
                job_id=context.job_id,
                run_id=context.run_id,
                query=input_text,
                limit=self.limit,
            )
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
        collector.append_stage(
            StageExecutionReceipt(
                receipt_id=f"stage:{context.stage_id}:complete",
                job_id=context.job_id,
                run_id=context.run_id,
                stage_id=context.stage_id,
                call_site=context.call_site,
                status=StageStatus.COMPLETED,
                attempt=context.attempt,
                round_number=context.round_number,
                detail=f"candidate_count={len(candidates)}",
            )
        )
        return RetrievalStageResult(retrieval_query=input_text, candidates=candidates)
