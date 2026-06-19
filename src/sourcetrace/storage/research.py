"""Deep Research persistence seams and in-memory adapters."""

from dataclasses import dataclass

from sourcetrace.storage.interfaces import (
    ResearchJobRepository,
    ResearchPersistence,
    ResearchProgressEventStore,
    ResearchResultRepository,
)
from sourcetrace.domain.research import ResearchJob, ResearchProgressEvent, ResearchResultArtifact

class InMemoryResearchJobRepository:
    """Research job repository backed by process-local dictionaries."""

    def __init__(self) -> None:
        self._jobs: dict[str, ResearchJob] = {}

    def save_job(self, job: ResearchJob) -> ResearchJob:
        self._jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> ResearchJob | None:
        return self._jobs.get(job_id)

    def list_jobs_for_owner(self, owner_id: str) -> tuple[ResearchJob, ...]:
        jobs = [job for job in self._jobs.values() if job.owner_id == owner_id]
        return tuple(sorted(jobs, key=lambda job: job.created_at))


class InMemoryResearchResultRepository:
    """Research result repository backed by process-local dictionaries."""

    def __init__(self) -> None:
        self._results: dict[str, ResearchResultArtifact] = {}

    def save_result(self, result: ResearchResultArtifact) -> ResearchResultArtifact:
        self._results[result.job_id] = result
        return result

    def get_result(self, job_id: str) -> ResearchResultArtifact | None:
        return self._results.get(job_id)


class InMemoryResearchProgressEventStore:
    """Research progress event store backed by process-local dictionaries."""

    def __init__(self) -> None:
        self._events: dict[str, list[ResearchProgressEvent]] = {}

    def append_event(self, event: ResearchProgressEvent) -> ResearchProgressEvent:
        self._events.setdefault(event.job_id, []).append(event)
        return event

    def list_events(self, job_id: str) -> tuple[ResearchProgressEvent, ...]:
        return tuple(self._events.get(job_id, ()))


def create_in_memory_research_persistence() -> ResearchPersistence:
    """Build the Deep Research persistence bundle from in-memory adapters."""

    return ResearchPersistence(
        jobs=InMemoryResearchJobRepository(),
        results=InMemoryResearchResultRepository(),
        progress=InMemoryResearchProgressEventStore(),
    )


__all__ = [
    "InMemoryResearchJobRepository",
    "InMemoryResearchProgressEventStore",
    "InMemoryResearchResultRepository",
    "ResearchJobRepository",
    "ResearchPersistence",
    "ResearchProgressEventStore",
    "ResearchResultRepository",
    "create_in_memory_research_persistence",
]
