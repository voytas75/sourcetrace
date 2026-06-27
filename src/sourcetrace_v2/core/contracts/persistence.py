from __future__ import annotations

from typing import Protocol

from sourcetrace_v2.core.domain.models import LlmExecutionReceipt, ResearchResultArtifact, StageExecutionReceipt


class ResultArtifactRepository(Protocol):
    def save_result(self, artifact: ResearchResultArtifact) -> ResearchResultArtifact:
        ...

    def get_result(self, *, job_id: str, run_id: str) -> ResearchResultArtifact | None:
        ...


class ReceiptRepository(Protocol):
    def append_stage(self, receipt: StageExecutionReceipt) -> StageExecutionReceipt:
        ...

    def append_llm(self, receipt: LlmExecutionReceipt) -> LlmExecutionReceipt:
        ...

    def list_stage_receipts(self, *, job_id: str, run_id: str) -> tuple[StageExecutionReceipt, ...]:
        ...

    def list_llm_receipts(self, *, job_id: str, run_id: str) -> tuple[LlmExecutionReceipt, ...]:
        ...
