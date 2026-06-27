from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sourcetrace_v2.core.domain.models import ExecutionRollup, LlmExecutionReceipt, ResearchResultArtifact, StageExecutionReceipt


class PersistedViewStatus(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True)
class PersistedExecutionView:
    status: PersistedViewStatus
    artifact: ResearchResultArtifact | None
    stage_receipts: tuple[StageExecutionReceipt, ...]
    llm_receipts: tuple[LlmExecutionReceipt, ...]
    rollup: ExecutionRollup
