from __future__ import annotations

from typing import Protocol

from sourcetrace_v2.core.domain.models import LlmExecutionReceipt, ResearchResultArtifact, RunPersistenceMarker, StageExecutionReceipt


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


class RunMarkerRepository(Protocol):
    def save_run_marker(self, marker: RunPersistenceMarker) -> RunPersistenceMarker:
        ...

    def get_run_marker(self, *, job_id: str, run_id: str) -> RunPersistenceMarker | None:
        ...
