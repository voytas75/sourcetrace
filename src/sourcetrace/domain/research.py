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
    GENERAL = "general"


class ResearchComplexity(str, Enum):
    """Coarse difficulty band derived from the user query."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ResearchPlanStrategy(str, Enum):
    """Small bounded planning strategy set for Deep Research."""

    DIRECT_ANSWER = "direct_answer"
    PROCEDURAL_RESEARCH = "procedural_research"
    BROAD_RESEARCH = "broad_research"
    NEWS_RESEARCH = "news_research"
    MARKET_SCAN = "market_scan"


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


class ResearchTerminationReason(str, Enum):
    """Small operator-facing terminal/recovery reason surface."""

    CANCELLED = "cancelled"
    INTERRUPTED_ON_RECOVERY = "interrupted_on_recovery"
    PROVIDER_FAILURE = "provider_failure"
    PARTIAL_SALVAGE = "partial_salvage"


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
class ProblemAnalysis:
    """Minimal structured problem framing derived for each research job."""

    query_class: ResearchQueryClass = ResearchQueryClass.GENERAL
    complexity: ResearchComplexity = ResearchComplexity.MEDIUM
    goal: str = ""
    focus_areas: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    analysis_version: str = "problem_analyzer_v1"


@dataclass(frozen=True)
class ResearchExecutionPlanStep:
    """One bounded planning step for a research run."""

    step_id: str
    kind: str
    objective: str
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResearchExecutionPlan:
    """Compact explicit execution plan derived from problem analysis."""

    plan_version: str = "planner_v2"
    strategy: ResearchPlanStrategy = ResearchPlanStrategy.DIRECT_ANSWER
    objective: str = ""
    steps: tuple[ResearchExecutionPlanStep, ...] = ()


@dataclass(frozen=True)
class ResearchEvidencePack:
    """Durable grouped evidence pack used by synthesis."""

    pack_version: str = "evidence_pack_v1"
    query_class: ResearchQueryClass = ResearchQueryClass.GENERAL
    core: tuple[ResearchFinding, ...] = ()
    supporting: tuple[ResearchFinding, ...] = ()
    background: tuple[ResearchFinding, ...] = ()
    has_direct_procedural_evidence: bool = False


@dataclass(frozen=True)
class ResearchBranchProposal:
    """One bounded analytical branch candidate for later execution/evaluation."""

    branch_id: str
    label: str
    objective: str


@dataclass(frozen=True)
class ResearchBranchProposalSet:
    """Deterministic branch proposal set for eligible research queries."""

    proposal_version: str = "branch_proposal_v1"
    eligible: bool = False
    reason: str = "not_eligible"
    branches: tuple[ResearchBranchProposal, ...] = ()


@dataclass(frozen=True)
class ResearchBranchScore:
    """Deterministic score for one proposed analytical branch."""

    branch_id: str
    coverage_score: float = 0.0
    evidence_fit_score: float = 0.0
    priority_score: float = 0.0
    combined_score: float = 0.0


@dataclass(frozen=True)
class ResearchBranchEvaluation:
    """Bounded evaluation artifact over a branch proposal set."""

    evaluation_version: str = "branch_evaluator_v1"
    selected_branch_ids: tuple[str, ...] = ()
    scores: tuple[ResearchBranchScore, ...] = ()


@dataclass(frozen=True)
class ResearchReflection:
    """Deterministic post-result reflection artifact."""

    reflection_version: str = "reflection_v1"
    goal_coverage: str = "partial"
    missing_topics: tuple[str, ...] = ()
    weak_evidence_areas: tuple[str, ...] = ()
    should_follow_up: bool = False
    recommended_follow_up: str | None = None


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
    problem_analysis: ProblemAnalysis | None = None
    execution_plan: ResearchExecutionPlan | None = None
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

    query_class: ResearchQueryClass = ResearchQueryClass.GENERAL
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
    problem_analysis_snapshot: ProblemAnalysis | None = None
    execution_plan_snapshot: ResearchExecutionPlan | None = None
    reflection_snapshot: ResearchReflection | None = None
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
    problem_analysis: ProblemAnalysis | None = None
    execution_plan: ResearchExecutionPlan | None = None
    evidence_pack: ResearchEvidencePack | None = None
    branch_proposals: ResearchBranchProposalSet | None = None
    branch_evaluation: ResearchBranchEvaluation | None = None
    reflection: ResearchReflection | None = None
    evaluation: ResearchEvaluationArtifact | None = None
    created_at: str = ""
    completed_at: str | None = None


__all__ = [
    "CompiledResearchArtifact",
    "CompiledResearchArtifactLint",
    "CompiledResearchArtifactLintStatus",
    "CompiledResearchClaim",
    "CompiledResearchEvidenceRef",
    "ProblemAnalysis",
    "ResearchBranchEvaluation",
    "ResearchBranchProposal",
    "ResearchBranchProposalSet",
    "ResearchBranchScore",
    "ResearchReflection",
    "ResearchEvidencePack",
    "ResearchExecutionPlan",
    "ResearchExecutionPlanStep",
    "ResearchCompletionMode",
    "ResearchComplexity",
    "ResearchEvaluationArtifact",
    "ResearchEvaluationVerdict",
    "ResearchFinding",
    "ResearchJob",
    "ResearchPlanStrategy",
    "ResearchJobStatus",
    "ResearchPhase",
    "ResearchProgressEvent",
    "ResearchQueryClass",
    "ResearchResultArtifact",
    "ResearchSettings",
    "ResearchSource",
    "ResearchStats",
    "ResearchTerminationReason",
]
