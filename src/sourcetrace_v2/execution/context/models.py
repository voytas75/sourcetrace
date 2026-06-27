from __future__ import annotations

from dataclasses import dataclass

from sourcetrace_v2.core.domain.identifiers import FeatureId, StageId


@dataclass(frozen=True)
class ExecutionContext:
    job_id: str
    run_id: str
    feature: FeatureId
    stage_id: StageId
    call_site: str
    attempt: int = 1
    round_number: int | None = None
