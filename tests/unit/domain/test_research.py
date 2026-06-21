from sourcetrace.domain import (
    CompiledResearchArtifact,
    CompiledResearchArtifactLint,
    CompiledResearchArtifactLintStatus,
    CompiledResearchClaim,
    CompiledResearchEvidenceRef,
    ResearchCompletionMode,
    ResearchEvaluationArtifact,
    ResearchEvaluationVerdict,
    ResearchJob,
    ResearchJobStatus,
    ResearchPhase,
    ResearchProgressEvent,
    ResearchQueryClass,
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
        evaluation=ResearchEvaluationArtifact(
            query_class=ResearchQueryClass.BROAD_CONCEPT,
            source_quality_verdict=ResearchEvaluationVerdict.MIXED,
        ),
        created_at="2026-06-19T07:00:00+00:00",
    )
    compiled = CompiledResearchArtifact(
        artifact_id="cra-rj-1",
        source_job_id="rj-1",
        owner_id="user-1",
        query="deep research architecture",
        query_class=ResearchQueryClass.BROAD_CONCEPT,
        title="Deep research architecture",
        summary="Short summary",
        current_answer="Current answer",
        key_claims=(CompiledResearchClaim(text="One claim", evidence_refs=("https://example.test",)),),
        supporting_evidence=(CompiledResearchEvidenceRef(url="https://example.test", title="Example", summary="Summary"),),
        created_at="2026-06-19T07:00:00+00:00",
    )
    lint = CompiledResearchArtifactLint(
        lint_id="crl-cra-rj-1",
        artifact_id="cra-rj-1",
        owner_id="user-1",
        status=CompiledResearchArtifactLintStatus.HEALTHY,
        created_at="2026-06-19T07:00:00+00:00",
    )

    assert job.settings.category == "tech"
    assert event.phase is ResearchPhase.PLANNING
    assert artifact.completion_mode is ResearchCompletionMode.FULL
    assert artifact.evaluation is not None
    assert artifact.evaluation.query_class is ResearchQueryClass.BROAD_CONCEPT
    assert compiled.query_class is ResearchQueryClass.BROAD_CONCEPT
    assert compiled.key_claims[0].text == "One claim"
    assert lint.status is CompiledResearchArtifactLintStatus.HEALTHY
