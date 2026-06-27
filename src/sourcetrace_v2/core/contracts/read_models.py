from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sourcetrace_v2.core.domain.models import ExecutionRollup, LlmExecutionReceipt, ResearchResultArtifact, RunPersistenceMarker, StageExecutionReceipt


class PersistedViewStatus(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    INCOMPLETE = "incomplete"


class PersistenceCompleteness(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    ABSENT = "absent"


@dataclass(frozen=True)
class PersistedRunEnvelope:
    job_id: str
    run_id: str
    status: PersistedViewStatus
    persistence_completeness: PersistenceCompleteness
    artifact_present: bool
    marker_present: bool
    marker_state: str | None


@dataclass(frozen=True)
class PersistedExecutionView:
    status: PersistedViewStatus
    envelope: PersistedRunEnvelope
    artifact: ResearchResultArtifact | None
    marker: RunPersistenceMarker | None
    stage_receipts: tuple[StageExecutionReceipt, ...]
    llm_receipts: tuple[LlmExecutionReceipt, ...]
    rollup: ExecutionRollup
