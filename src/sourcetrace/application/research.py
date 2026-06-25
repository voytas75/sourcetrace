"""Application contracts and runtime seams for Deep Research."""

from dataclasses import dataclass, field
from typing import Protocol

from sourcetrace.domain.research import (
    PlanningAnalysis,
    ProblemAnalysis,
    ResearchExecutionPlan,
    ResearchJob,
    ResearchProgressEvent,
    ResearchResultArtifact,
    ResearchSettings,
)


@dataclass(frozen=True)
class SearchHit:
    """Normalized search hit used by the engine loop."""

    url: str
    title: str
    snippet: str


@dataclass(frozen=True)
class ExtractedFinding:
    """Normalized extracted finding from one hit."""

    url: str
    title: str
    summary: str
    pdf_triage_verdict: str | None = None
    pdf_triage_notes: str | None = None


@dataclass(frozen=True)
class SynthesisResult:
    """Intermediate synthesis output used to evolve the report."""

    report_markdown: str
    answer_summary: str
    should_continue: bool


@dataclass(frozen=True)
class PdfIngestResult:
    """Structured result returned by an optional PDF ingest backend."""

    relevant: bool
    confidence: float
    document_scope: str
    entity_match_summary: str
    key_findings: tuple[str, ...] = ()
    evidence_pages: tuple[int, ...] = ()


@dataclass(frozen=True)
class ResearchJobStartRequest:
    """Input contract for starting a Deep Research job."""

    owner_id: str
    query: str
    settings: ResearchSettings = field(default_factory=ResearchSettings)


@dataclass(frozen=True)
class ResearchJobStartOutcome:
    """Result of accepting a Deep Research job."""

    request: ResearchJobStartRequest
    job: ResearchJob


@dataclass(frozen=True)
class ResearchJobStatusOutcome:
    """Read model for one job status request."""

    job: ResearchJob
    progress: tuple[ResearchProgressEvent, ...] = ()


@dataclass(frozen=True)
class ResearchJobResultOutcome:
    """Read model for one job result request."""

    job: ResearchJob
    result: ResearchResultArtifact | None


@dataclass(frozen=True)
class ResearchJobListOutcome:
    """Owner-scoped list of persisted research jobs."""

    owner_id: str
    jobs: tuple[ResearchJob, ...]


class ResearchPlanningAnalyzer(Protocol):
    """Execution seam for deriving planning analysis from the raw user query."""

    def __call__(self, query: str) -> PlanningAnalysis:
        ...


class ResearchPlanner(Protocol):
    """Execution seam for building a research plan from problem analysis."""

    def __call__(
        self,
        query: str,
        *,
        problem_analysis: ProblemAnalysis,
        planning_analysis: PlanningAnalysis | None = None,
    ) -> ResearchExecutionPlan:
        ...


class ResearchQueryGenerator(Protocol):
    """Execution seam for generating search queries from a plan."""

    def __call__(
        self,
        plan: ResearchExecutionPlan,
        *,
        round_number: int,
        planning_analysis: PlanningAnalysis | None = None,
    ) -> tuple[str, ...]:
        ...


class ResearchSearchAdapter(Protocol):
    """Execution seam for returning normalized search hits."""

    def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
        ...


class ResearchExtractor(Protocol):
    """Execution seam for converting normalized hits into findings."""

    def __call__(self, hits: tuple[SearchHit, ...]) -> tuple[ExtractedFinding, ...]:
        ...


class ResearchSynthesizer(Protocol):
    """Execution seam for evolving a report from extracted findings."""

    def __call__(
        self,
        *,
        query: str,
        round_number: int,
        findings: tuple[ExtractedFinding, ...],
        previous_report: str | None,
    ) -> SynthesisResult:
        ...


class ResearchPdfIngestor(Protocol):
    """Optional execution seam for ingesting a verified PDF artifact."""

    def __call__(
        self,
        *,
        query: str,
        url: str,
        title: str,
        triage_verdict: str,
    ) -> PdfIngestResult:
        ...


class ExternalPdfAnalyzer(Protocol):
    """External analyzer contract for reading a PDF URL and returning structured evidence."""

    def __call__(
        self,
        *,
        query: str,
        url: str,
        title: str,
        triage_verdict: str,
    ) -> PdfIngestResult:
        ...


class ResearchJobStarter(Protocol):
    """Execution seam for accepting a Deep Research job."""

    def __call__(self, request: ResearchJobStartRequest) -> ResearchJobStartOutcome:
        ...


class ResearchJobStatusReader(Protocol):
    """Execution seam for reading Deep Research job status."""

    def __call__(self, job_id: str) -> ResearchJobStatusOutcome | None:
        ...


class ResearchJobCanceller(Protocol):
    """Execution seam for cancelling a Deep Research job."""

    def __call__(self, job_id: str) -> ResearchJob | None:
        ...


class ResearchJobResultReader(Protocol):
    """Execution seam for reading a Deep Research result artifact."""

    def __call__(self, job_id: str) -> ResearchJobResultOutcome | None:
        ...


class ResearchJobLister(Protocol):
    """Execution seam for listing Deep Research jobs by owner."""

    def __call__(self, owner_id: str) -> ResearchJobListOutcome:
        ...


class ResearchWorker(Protocol):
    """Execution seam for running one Deep Research job."""

    def __call__(self, job_id: str) -> ResearchResultArtifact | None:
        ...


@dataclass(frozen=True)
class ResearchExecution:
    """Bundle for Deep Research lifecycle use cases."""

    start_job: ResearchJobStarter
    get_job_status: ResearchJobStatusReader
    cancel_job: ResearchJobCanceller
    get_job_result: ResearchJobResultReader
    list_jobs: ResearchJobLister
    run_job: ResearchWorker


__all__ = [
    "ExtractedFinding",
    "ResearchExecution",
    "ResearchExtractor",
    "ResearchJobCanceller",
    "ResearchJobListOutcome",
    "ResearchJobLister",
    "ResearchJobResultOutcome",
    "ResearchJobResultReader",
    "ResearchJobStartOutcome",
    "ResearchJobStartRequest",
    "ResearchJobStarter",
    "ResearchJobStatusOutcome",
    "ResearchJobStatusReader",
    "ResearchPlanningAnalyzer",
    "ResearchPlanner",
    "ResearchQueryGenerator",
    "ResearchSearchAdapter",
    "ResearchSynthesizer",
    "ResearchWorker",
    "SearchHit",
    "SynthesisResult",
]
