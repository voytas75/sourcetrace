"""Deep Research domain records and enums."""

from dataclasses import dataclass, field
from enum import Enum


class ResearchEvaluationVerdict(str, Enum):
    """Structured post-result evaluation verdict bands."""

    STRONG = "strong"
    MIXED = "mixed"
    WEAK = "weak"


class ResearchQueryClass(str, Enum):
    """Query-class buckets for post-result evaluation."""

    MARKET_SYMBOL = "market_symbol"
    PROCEDURAL_ADMIN = "procedural_admin"
    BROAD_CONCEPT = "broad_concept"
    CURRENT_NEWS = "current_news"
    UNKNOWN = "unknown"


class ResearchJobStatus(str, Enum):
    """Top-level lifecycle state for a Deep Research job."""

    QUEUED = "queued"
    PROBING = "probing"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


class ResearchPhase(str, Enum):
    """Runtime phase emitted in progress events."""

    PROBING = "probing"
    PLANNING = "planning"
    SEARCHING = "searching"
    READING = "reading"
    ANALYZING = "analyzing"
    WRITING = "writing"
    WARNING = "warning"
    ERROR = "error"


class ResearchCompletionMode(str, Enum):
    """How a completed artifact was produced."""

    FULL = "full"
    PARTIAL_TIMEOUT = "partial_timeout"
    PARTIAL_ERROR = "partial_error"
    FALLBACK = "fallback"


class CompiledResearchArtifactLintStatus(str, Enum):
    """Overall health status for a compiled research artifact."""

    HEALTHY = "healthy"
    NEEDS_REVIEW = "needs_review"
    WEAK = "weak"


@dataclass(frozen=True)
class ResearchSettings:
    """Execution settings for a Deep Research job."""

    max_rounds: int = 6
    max_time_seconds: int = 300
    search_provider: str | None = None
    endpoint_id: str | None = None
    model: str | None = None
    extraction_timeout_seconds: int = 90
    extraction_concurrency: int = 3
    category: str | None = None


@dataclass(frozen=True)
class ResearchSource:
    """Persisted user-facing source reference."""

    url: str
    title: str
    image: str | None = None


@dataclass(frozen=True)
class ResearchFinding:
    """Persisted extracted evidence note."""

    url: str
    title: str
    summary: str


@dataclass(frozen=True)
class ResearchStats:
    """Basic run statistics stored with the artifact."""

    duration_seconds: int = 0
    rounds: int = 0
    queries: int = 0
    urls: int = 0
    model: str | None = None
    search_providers: tuple[str, ...] = ()
    pre_extraction_sources_seen: int = 0
    pre_extraction_sources_kept: int = 0
    pre_extraction_sources_dropped: int = 0
    authority_policy_applied: bool = False
    authority_filter_fallback_used: bool = False
    dropped_source_types: tuple[str, ...] = ()
    packed_core_count: int = 0
    packed_supporting_count: int = 0
    packed_background_count: int = 0


@dataclass(frozen=True)
class ResearchJob:
    """Durable Deep Research job record."""

    job_id: str
    owner_id: str
    query: str
    status: ResearchJobStatus
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    settings: ResearchSettings = field(default_factory=ResearchSettings)
    error: str | None = None


@dataclass(frozen=True)
class ResearchProgressEvent:
    """Progress event emitted while a research job runs."""

    job_id: str
    status: ResearchJobStatus
    phase: ResearchPhase
    round: int = 0
    queries: int = 0
    query_preview: str | None = None
    query_list: tuple[str, ...] = ()
    providers_attempted: tuple[str, ...] = ()
    total_sources: int = 0
    new_sources: int = 0
    total_findings: int = 0
    url: str | None = None
    title: str | None = None
    message: str | None = None
    final: bool = False


@dataclass(frozen=True)
class ResearchEvaluationArtifact:
    """Structured post-result evaluation artifact for a completed research job."""

    query_class: ResearchQueryClass = ResearchQueryClass.UNKNOWN
    source_quality_verdict: ResearchEvaluationVerdict = ResearchEvaluationVerdict.MIXED
    source_quality_reasons: tuple[str, ...] = ()
    relevance_verdict: ResearchEvaluationVerdict = ResearchEvaluationVerdict.MIXED
    relevance_risks: tuple[str, ...] = ()
    truthfulness_verdict: ResearchEvaluationVerdict = ResearchEvaluationVerdict.MIXED
    overclaim_risks: tuple[str, ...] = ()
    missing_checks: tuple[str, ...] = ()
    recommended_next_check: str = ""
    should_revise_report: bool = False


@dataclass(frozen=True)
class CompiledResearchEvidenceRef:
    """Compact evidence reference stored on a compiled research artifact."""

    url: str
    title: str
    summary: str


@dataclass(frozen=True)
class CompiledResearchClaim:
    """Concise claim carried by a compiled research artifact."""

    text: str
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class CompiledResearchArtifact:
    """Durable compiled artifact derived from a completed research result."""

    artifact_id: str
    source_job_id: str
    owner_id: str
    query: str
    query_class: ResearchQueryClass
    title: str
    summary: str
    current_answer: str
    key_claims: tuple[CompiledResearchClaim, ...] = ()
    supporting_evidence: tuple[CompiledResearchEvidenceRef, ...] = ()
    open_questions: tuple[str, ...] = ()
    next_checks: tuple[str, ...] = ()
    source_refs: tuple[ResearchSource, ...] = ()
    evaluation_snapshot: ResearchEvaluationArtifact | None = None
    created_at: str = ""


@dataclass(frozen=True)
class CompiledResearchArtifactLint:
    """Deterministic lint/health view over one compiled research artifact."""

    lint_id: str
    artifact_id: str
    owner_id: str
    status: CompiledResearchArtifactLintStatus
    completeness_verdict: ResearchEvaluationVerdict = ResearchEvaluationVerdict.MIXED
    evidence_verdict: ResearchEvaluationVerdict = ResearchEvaluationVerdict.MIXED
    followup_verdict: ResearchEvaluationVerdict = ResearchEvaluationVerdict.MIXED
    risk_flags: tuple[str, ...] = ()
    missing_sections: tuple[str, ...] = ()
    recommended_repairs: tuple[str, ...] = ()
    recommended_next_action: str = ""
    created_at: str = ""


@dataclass(frozen=True)
class ResearchResultArtifact:
    """Durable result artifact for a finished Deep Research job."""

    job_id: str
    owner_id: str
    query: str
    status: ResearchJobStatus
    completion_mode: ResearchCompletionMode
    result: str
    raw_report: str
    category: str | None = None
    stats: ResearchStats = field(default_factory=ResearchStats)
    sources: tuple[ResearchSource, ...] = ()
    raw_findings: tuple[ResearchFinding, ...] = ()
    evaluation: ResearchEvaluationArtifact | None = None
    created_at: str = ""
    completed_at: str | None = None


__all__ = [
    "CompiledResearchArtifact",
    "CompiledResearchArtifactLint",
    "CompiledResearchArtifactLintStatus",
    "CompiledResearchClaim",
    "CompiledResearchEvidenceRef",
    "ResearchCompletionMode",
    "ResearchEvaluationArtifact",
    "ResearchEvaluationVerdict",
    "ResearchFinding",
    "ResearchJob",
    "ResearchJobStatus",
    "ResearchPhase",
    "ResearchProgressEvent",
    "ResearchQueryClass",
    "ResearchResultArtifact",
    "ResearchSettings",
    "ResearchSource",
    "ResearchStats",
]
