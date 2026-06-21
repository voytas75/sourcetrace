from sourcetrace.domain import ResearchJob, ResearchJobStatus, ResearchSettings
from sourcetrace.storage import (
    InMemoryCompiledResearchArtifactLintRepository,
    InMemoryCompiledResearchArtifactRepository,
    InMemoryResearchJobRepository,
    InMemoryResearchProgressEventStore,
    InMemoryResearchResultRepository,
    ResearchPersistence,
    create_in_memory_research_persistence,
)


def test_research_storage_package_re_exports_are_available() -> None:
    persistence = create_in_memory_research_persistence()
    assert isinstance(persistence.jobs, InMemoryResearchJobRepository)
    assert isinstance(persistence.results, InMemoryResearchResultRepository)
    assert isinstance(persistence.progress, InMemoryResearchProgressEventStore)
    assert isinstance(persistence.compiled, InMemoryCompiledResearchArtifactRepository)
    assert isinstance(persistence.compiled_lint, InMemoryCompiledResearchArtifactLintRepository)


def test_research_persistence_container_shape() -> None:
    persistence = create_in_memory_research_persistence()
    bundle = ResearchPersistence(
        jobs=persistence.jobs,
        results=persistence.results,
        progress=persistence.progress,
        compiled=persistence.compiled,
        compiled_lint=persistence.compiled_lint,
    )
    assert bundle.jobs is persistence.jobs


def test_in_memory_research_job_repository_lists_owner_jobs() -> None:
    repo = InMemoryResearchJobRepository()
    job = ResearchJob(
        job_id="rj-1",
        owner_id="user-1",
        query="deep research architecture",
        status=ResearchJobStatus.QUEUED,
        created_at="2026-06-19T07:00:00+00:00",
        settings=ResearchSettings(),
    )
    repo.save_job(job)

    listed = repo.list_jobs_for_owner("user-1")

    assert listed == (job,)
