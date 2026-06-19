"""Deep Research domain records and enums."""

from dataclasses import dataclass, field
from enum import Enum


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
    total_sources: int = 0
    new_sources: int = 0
    total_findings: int = 0
    url: str | None = None
    title: str | None = None
    message: str | None = None
    final: bool = False


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
    created_at: str = ""
    completed_at: str | None = None


__all__ = [
    "ResearchCompletionMode",
    "ResearchFinding",
    "ResearchJob",
    "ResearchJobStatus",
    "ResearchPhase",
    "ResearchProgressEvent",
    "ResearchResultArtifact",
    "ResearchSettings",
    "ResearchSource",
    "ResearchStats",
]
