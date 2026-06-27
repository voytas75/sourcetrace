from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime

from sourcetrace_v2.core.domain.identifiers import (
    DegradationReason,
    FeatureId,
    JobStatus,
    ReceiptCoverageStatus,
    StageId,
    StageStatus,
)


@dataclass(frozen=True)
class ResearchJob:
    job_id: str
    feature: FeatureId = FeatureId.DEEP_RESEARCH
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def mark_running(self) -> "ResearchJob":
        return replace(self, status=JobStatus.RUNNING)

    def mark_done(self) -> "ResearchJob":
        return replace(self, status=JobStatus.DONE)

    def mark_error(self) -> "ResearchJob":
        return replace(self, status=JobStatus.ERROR)


@dataclass(frozen=True)
class ResearchRun:
    run_id: str
    job_id: str
    feature: FeatureId = FeatureId.DEEP_RESEARCH
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class RetrievedEvidenceCandidate:
    candidate_id: str
    job_id: str
    run_id: str
    provider: str
    query: str
    title: str
    url: str
    snippet: str = ""
    rank: int = 1


@dataclass(frozen=True)
class ResearchResultArtifact:
    job_id: str
    run_id: str
    result_text: str
    summary: str = ""
    evidence_query: str = ""
    evidence_candidates: tuple[RetrievedEvidenceCandidate, ...] = ()


@dataclass(frozen=True)
class StageExecutionReceipt:
    receipt_id: str
    job_id: str
    run_id: str
    stage_id: StageId
    call_site: str
    status: StageStatus
    attempt: int = 1
    round_number: int | None = None
    detail: str = ""
    degradation_reason: DegradationReason | None = None


@dataclass(frozen=True)
class LlmExecutionReceipt:
    receipt_id: str
    job_id: str
    run_id: str
    stage_id: StageId
    call_site: str
    profile: str
    provider: str
    model: str
    coverage_status: ReceiptCoverageStatus = ReceiptCoverageStatus.TRACKED
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    finish_reason: str | None = None
    degradation_reason: DegradationReason | None = None


@dataclass(frozen=True)
class ExecutionRollup:
    job_id: str
    run_id: str
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    degraded_calls: int = 0
    failed_stages: int = 0


@dataclass(frozen=True)
class RunPersistenceMarker:
    job_id: str
    run_id: str
    status: str = "committed"
