from sourcetrace.domain import (
    CompiledResearchArtifact,
    CompiledResearchArtifactLint,
    CompiledResearchArtifactLintStatus,
    CompiledResearchClaim,
    CompiledResearchEvidenceRef,
    ProblemAnalysis,
    ResearchBranchEvaluation,
    ResearchBranchProposalSet,
    ResearchBranchScore,
    ResearchCompletionMode,
    ResearchReflection,
    ResearchComplexity,
    ResearchEvaluationArtifact,
    ResearchEvidencePack,
    ResearchExecutionPlan,
    ResearchExecutionPlanStep,
    ResearchEvaluationVerdict,
    ResearchJob,
    ResearchJobStatus,
    ResearchPhase,
    ResearchPlanStrategy,
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
        problem_analysis=ProblemAnalysis(
            query_class=ResearchQueryClass.BROAD_CONCEPT,
            complexity=ResearchComplexity.HIGH,
            goal="deep research architecture",
            focus_areas=("definition", "system_shape"),
        ),
        execution_plan=ResearchExecutionPlan(
            strategy=ResearchPlanStrategy.BROAD_RESEARCH,
            objective="deep research architecture",
            steps=(
                ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Collect high-signal conceptual and technical sources."),
            ),
        ),
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
        problem_analysis=ProblemAnalysis(
            query_class=ResearchQueryClass.BROAD_CONCEPT,
            complexity=ResearchComplexity.HIGH,
            goal="deep research architecture",
        ),
        execution_plan=ResearchExecutionPlan(
            strategy=ResearchPlanStrategy.BROAD_RESEARCH,
            objective="deep research architecture",
            steps=(
                ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Collect high-signal conceptual and technical sources."),
            ),
        ),
        evidence_pack=ResearchEvidencePack(query_class=ResearchQueryClass.BROAD_CONCEPT),
        branch_proposals=ResearchBranchProposalSet(eligible=True, reason="broad_or_high_complexity_query"),
        branch_evaluation=ResearchBranchEvaluation(
            selected_branch_ids=("branch-1",),
            scores=(ResearchBranchScore(branch_id="branch-1", combined_score=0.9),),
        ),
        reflection=ResearchReflection(goal_coverage="partial", should_follow_up=True, recommended_follow_up="Investigate missing topic: tradeoffs."),
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
        problem_analysis_snapshot=ProblemAnalysis(
            query_class=ResearchQueryClass.BROAD_CONCEPT,
            complexity=ResearchComplexity.HIGH,
            goal="deep research architecture",
        ),
        execution_plan_snapshot=ResearchExecutionPlan(
            strategy=ResearchPlanStrategy.BROAD_RESEARCH,
            objective="deep research architecture",
            steps=(
                ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Collect high-signal conceptual and technical sources."),
            ),
        ),
        reflection_snapshot=ResearchReflection(goal_coverage="partial", should_follow_up=True, recommended_follow_up="Investigate missing topic: tradeoffs."),
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
    assert job.problem_analysis is not None
    assert job.execution_plan is not None
    assert event.phase is ResearchPhase.PLANNING
    assert artifact.completion_mode is ResearchCompletionMode.FULL
    assert artifact.problem_analysis is not None
    assert artifact.execution_plan is not None
    assert artifact.evidence_pack is not None
    assert artifact.branch_proposals is not None
    assert artifact.branch_evaluation is not None
    assert artifact.reflection is not None
    assert artifact.evaluation is not None
    assert artifact.evaluation.query_class is ResearchQueryClass.BROAD_CONCEPT
    assert compiled.query_class is ResearchQueryClass.BROAD_CONCEPT
    assert compiled.problem_analysis_snapshot is not None
    assert compiled.execution_plan_snapshot is not None
    assert compiled.reflection_snapshot is not None
    assert compiled.key_claims[0].text == "One claim"
    assert lint.status is CompiledResearchArtifactLintStatus.HEALTHY
