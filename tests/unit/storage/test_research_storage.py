from sourcetrace.domain import ResearchJob, ResearchJobStatus, ResearchSettings
from sourcetrace.storage import (
    InMemoryCompiledResearchArtifactLintRepository,
    InMemoryCompiledResearchArtifactRepository,
    InMemoryResearchJobRepository,
    InMemoryResearchProgressEventStore,
    InMemoryResearchResultRepository,
    ResearchPersistence,
    create_file_backed_research_persistence,
    create_in_memory_research_persistence,
    recover_interrupted_research_jobs,
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


def test_recover_interrupted_research_jobs_marks_inflight_jobs_as_recovered_errors(tmp_path) -> None:
    persistence = create_file_backed_research_persistence(tmp_path)
    job = ResearchJob(
        job_id="rj-recover",
        owner_id="user-1",
        query="deep research architecture",
        status=ResearchJobStatus.RUNNING,
        created_at="2026-06-24T07:00:00+00:00",
        started_at="2026-06-24T07:01:00+00:00",
        settings=ResearchSettings(),
    )
    persistence.jobs.save_job(job)

    recovered = recover_interrupted_research_jobs(tmp_path)

    reloaded = create_file_backed_research_persistence(tmp_path)
    persisted_job = reloaded.jobs.get_job("rj-recover")
    progress = reloaded.progress.list_events("rj-recover")

    assert recovered == ("rj-recover",)
    assert persisted_job is not None
    assert persisted_job.status is ResearchJobStatus.ERROR
    assert persisted_job.error == "interrupted_on_recovery"
    assert persisted_job.completed_at is not None
    assert progress[-1].final is True
    assert progress[-1].message == "Research job was interrupted by process restart and recovered as error."
