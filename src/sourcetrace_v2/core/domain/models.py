from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime

from sourcetrace_v2.core.contracts.trust_metadata import SourceTraceTrustMetadata
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
class PdfEvidenceContext:
    document_scope: str = ""
    entity_match_summary: str = ""
    key_findings: tuple[str, ...] = ()


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
    source_type: str = "unknown"
    pdf_context: PdfEvidenceContext | None = None
    trust_metadata: SourceTraceTrustMetadata | None = None


@dataclass(frozen=True)
class RetrievalPoolSemanticFitSnapshot:
    status: str = "unknown"
    focus_term_count: int = 0
    matched_term_count: int = 0
    matched_terms: tuple[str, ...] = ()
    best_candidate_rank: int | None = None


@dataclass(frozen=True)
class RetrievalSemanticFitDiagnostics:
    contract_version: str = "retrieval-semantic-fit-guard-v1"
    focus_terms: tuple[str, ...] = ()
    pretrim: RetrievalPoolSemanticFitSnapshot = field(default_factory=RetrievalPoolSemanticFitSnapshot)
    trimmed: RetrievalPoolSemanticFitSnapshot = field(default_factory=RetrievalPoolSemanticFitSnapshot)
    insufficiency_stage: str = "unknown"
    pretrim_explicit: bool = False


@dataclass(frozen=True)
class ResearchResultArtifact:
    job_id: str
    run_id: str
    result_text: str
    summary: str = ""
    evidence_query: str = ""
    evidence_candidates: tuple[RetrievedEvidenceCandidate, ...] = ()
    pretrim_evidence_candidates: tuple[RetrievedEvidenceCandidate, ...] = ()
    retrieval_diagnostics: RetrievalSemanticFitDiagnostics | None = None
    # These describe the candidate pool before it is trimmed for downstream
    # selection. They intentionally do not retain the full raw pool.
    retrieval_candidate_pool_count: int = 0
    retrieval_semantic_fit_status: str = "unknown"
    retrieval_best_focus_coverage: float | None = None


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
