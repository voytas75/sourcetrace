"""Deep Research persistence seams and in-memory adapters."""

from dataclasses import dataclass

from sourcetrace.storage.interfaces import (
    CompiledResearchArtifactLintRepository,
    CompiledResearchArtifactRepository,
    ResearchJobRepository,
    ResearchPersistence,
    ResearchProgressEventStore,
    ResearchResultRepository,
)
from sourcetrace.domain.research import CompiledResearchArtifact, CompiledResearchArtifactLint, ResearchJob, ResearchProgressEvent, ResearchResultArtifact

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


class InMemoryCompiledResearchArtifactRepository:
    """Compiled research artifact repository backed by process-local dictionaries."""

    def __init__(self) -> None:
        self._artifacts: dict[str, CompiledResearchArtifact] = {}

    def save_artifact(self, artifact: CompiledResearchArtifact) -> CompiledResearchArtifact:
        self._artifacts[artifact.artifact_id] = artifact
        return artifact

    def get_artifact(self, artifact_id: str) -> CompiledResearchArtifact | None:
        return self._artifacts.get(artifact_id)

    def list_artifacts_for_owner(self, owner_id: str) -> tuple[CompiledResearchArtifact, ...]:
        items = [artifact for artifact in self._artifacts.values() if artifact.owner_id == owner_id]
        return tuple(sorted(items, key=lambda artifact: artifact.created_at))


class InMemoryCompiledResearchArtifactLintRepository:
    """Compiled research artifact lint repository backed by process-local dictionaries."""

    def __init__(self) -> None:
        self._lints: dict[str, CompiledResearchArtifactLint] = {}
        self._artifact_to_lint: dict[str, str] = {}

    def save_lint(self, lint: CompiledResearchArtifactLint) -> CompiledResearchArtifactLint:
        self._lints[lint.lint_id] = lint
        self._artifact_to_lint[lint.artifact_id] = lint.lint_id
        return lint

    def get_lint(self, lint_id: str) -> CompiledResearchArtifactLint | None:
        return self._lints.get(lint_id)

    def get_lint_for_artifact(self, artifact_id: str) -> CompiledResearchArtifactLint | None:
        lint_id = self._artifact_to_lint.get(artifact_id)
        return self._lints.get(lint_id) if lint_id else None

    def list_lints_for_owner(self, owner_id: str) -> tuple[CompiledResearchArtifactLint, ...]:
        items = [lint for lint in self._lints.values() if lint.owner_id == owner_id]
        return tuple(sorted(items, key=lambda lint: lint.created_at))


def create_in_memory_research_persistence() -> ResearchPersistence:
    """Build the Deep Research persistence bundle from in-memory adapters."""

    return ResearchPersistence(
        jobs=InMemoryResearchJobRepository(),
        results=InMemoryResearchResultRepository(),
        progress=InMemoryResearchProgressEventStore(),
        compiled=InMemoryCompiledResearchArtifactRepository(),
        compiled_lint=InMemoryCompiledResearchArtifactLintRepository(),
    )


__all__ = [
    "InMemoryCompiledResearchArtifactLintRepository",
    "InMemoryCompiledResearchArtifactRepository",
    "InMemoryResearchJobRepository",
    "InMemoryResearchProgressEventStore",
    "InMemoryResearchResultRepository",
    "ResearchJobRepository",
    "ResearchPersistence",
    "ResearchProgressEventStore",
    "ResearchResultRepository",
    "create_in_memory_research_persistence",
]
