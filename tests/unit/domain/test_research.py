from sourcetrace.domain import (
    ResearchCompletionMode,
    ResearchJob,
    ResearchJobStatus,
    ResearchPhase,
    ResearchProgressEvent,
    ResearchResultArtifact,
    ResearchSettings,
    ResearchStats,
)


def test_research_domain_re_exports_are_available() -> None:
    settings = ResearchSettings(max_rounds=4, category="tech")
    job = ResearchJob(
        job_id="rj-1",
        owner_id="user-1",
        query="deep research architecture",
        status=ResearchJobStatus.QUEUED,
        created_at="2026-06-19T07:00:00+00:00",
        settings=settings,
    )
    event = ResearchProgressEvent(
        job_id="rj-1",
        status=ResearchJobStatus.RUNNING,
        phase=ResearchPhase.PLANNING,
        message="Planning.",
    )
    artifact = ResearchResultArtifact(
        job_id="rj-1",
        owner_id="user-1",
        query="deep research architecture",
        status=ResearchJobStatus.DONE,
        completion_mode=ResearchCompletionMode.FULL,
        result="ok",
        raw_report="raw",
        stats=ResearchStats(rounds=1),
        created_at="2026-06-19T07:00:00+00:00",
    )

    assert job.settings.category == "tech"
    assert event.phase is ResearchPhase.PLANNING
    assert artifact.completion_mode is ResearchCompletionMode.FULL
