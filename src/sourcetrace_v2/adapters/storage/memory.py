from __future__ import annotations

from dataclasses import dataclass, field

from sourcetrace_v2.core.domain.models import LlmExecutionReceipt, ResearchResultArtifact, StageExecutionReceipt


@dataclass
class InMemoryResultArtifactRepository:
    artifacts: dict[tuple[str, str], ResearchResultArtifact] = field(default_factory=dict)

    def save_result(self, artifact: ResearchResultArtifact) -> ResearchResultArtifact:
        self.artifacts[(artifact.job_id, artifact.run_id)] = artifact
        return artifact

    def get_result(self, *, job_id: str, run_id: str) -> ResearchResultArtifact | None:
        return self.artifacts.get((job_id, run_id))


@dataclass
class InMemoryReceiptRepository:
    stage_receipts: dict[tuple[str, str], list[StageExecutionReceipt]] = field(default_factory=dict)
    llm_receipts: dict[tuple[str, str], list[LlmExecutionReceipt]] = field(default_factory=dict)

    def append_stage(self, receipt: StageExecutionReceipt) -> StageExecutionReceipt:
        self.stage_receipts.setdefault((receipt.job_id, receipt.run_id), []).append(receipt)
        return receipt

    def append_llm(self, receipt: LlmExecutionReceipt) -> LlmExecutionReceipt:
        self.llm_receipts.setdefault((receipt.job_id, receipt.run_id), []).append(receipt)
        return receipt

    def list_stage_receipts(self, *, job_id: str, run_id: str) -> tuple[StageExecutionReceipt, ...]:
        return tuple(self.stage_receipts.get((job_id, run_id), []))

    def list_llm_receipts(self, *, job_id: str, run_id: str) -> tuple[LlmExecutionReceipt, ...]:
        return tuple(self.llm_receipts.get((job_id, run_id), []))
