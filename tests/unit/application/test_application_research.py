from sourcetrace.application import (
    ExtractedFinding,
    FakeResearchWorker,
    ResearchJobManager,
    ResearchJobStartRequest,
    StubExtractor,
    StubQueryGenerator,
    SearchHit,
    SearxNGSearchAdapter,
)
from sourcetrace.application.research_runtime import (
    LlmResearchSynthesizer,
    ResearchSearchError,
    StubQueryGenerator,
    _authority_signal_score,
    _build_research_report_prompt,
    _classify_query,
    _compile_research_artifact,
    _derive_branch_proposals,
    _derive_problem_analysis,
    _derive_reflection,
    _evaluate_branch_proposals,
    _evaluate_research_result,
    _filter_hits_for_extraction,
    _is_relevant_hit,
    _lint_compiled_research_artifact,
    _looks_like_listing_page,
    _pack_evidence_for_synthesis,
    _search_rejection_summary,
    _procedural_query_bias,
    _procedural_directness_score,
    _procedural_query_variants,
    _procedural_task_match_score,
    _project_source_refs,
    _research_report_prompt_overlay,
    _top_findings,
    _to_research_evidence_pack,
    build_procedural_admin_unified_search_adapter,
    build_search_adapter,
)
from sourcetrace.domain import (
    CompiledResearchArtifact,
    CompiledResearchClaim,
    CompiledResearchArtifactLintStatus,
    CompiledResearchEvidenceRef,
    ProblemAnalysis,
    ResearchBranchEvaluation,
    ResearchBranchProposalSet,
    ResearchBranchScore,
    ResearchCompletionMode,
    ResearchReflection,
    ResearchComplexity,
    ResearchEvaluationArtifact,
    ResearchEvaluationVerdict,
    ResearchEvidencePack,
    ResearchExecutionPlan,
    ResearchExecutionPlanStep,
    ResearchFinding,
    ResearchJobStatus,
    ResearchPlanStrategy,
    ResearchQueryClass,
    ResearchResultArtifact,
    ResearchSource,
    ResearchStats,
)
from sourcetrace.storage import create_file_backed_research_persistence, create_in_memory_research_persistence


class DeterministicSearch:
    def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
        query_text = ' '.join(queries).lower()
        if 'sccm' in query_text or 'configuration baselines' in query_text:
            if round_number == 1:
                return (
                    SearchHit(
                        url="https://learn.microsoft.com/en-us/mem/configmgr/compliance/deploy-use/create-configuration-baselines",
                        title="Create configuration baselines - Configuration Manager | Microsoft Learn",
                        snippet="Create and deploy configuration baselines in Configuration Manager.",
                    ),
                    SearchHit(
                        url="https://learn.microsoft.com/en-us/mem/configmgr/compliance/deploy-use/monitor-compliance-settings",
                        title="Monitor compliance settings - Configuration Manager | Microsoft Learn",
                        snippet="Monitor compliant and non-compliant clients after deployment.",
                    ),
                )
            return (
                SearchHit(
                    url="https://learn.microsoft.com/en-us/mem/configmgr/compliance/deploy-use/create-configuration-items",
                    title="Create configuration items - Configuration Manager | Microsoft Learn",
                    snippet="Configuration items feed baselines and remediation workflows.",
                ),
            )
        if round_number == 1:
            return (
                SearchHit(
                    url="https://example.test/odysseus-architecture",
                    title="Odysseus Deep Research Architecture",
                    snippet="Async jobs, progress streaming, and persisted artifacts.",
                ),
                SearchHit(
                    url="https://example.test/source-trace-design",
                    title="SourceTrace Deep Research Design",
                    snippet="Lifecycle-first implementation reduces rework.",
                ),
            )
        return (
            SearchHit(
                url="https://example.test/stop-rails",
                title="Deterministic Stop Rails",
                snippet="Bound the loop with max rounds and low-yield guards.",
            ),
        )


def _build_test_execution():
    persistence = create_in_memory_research_persistence()
    manager = ResearchJobManager(persistence)
    worker = FakeResearchWorker(persistence, search=DeterministicSearch())
    return persistence, manager, worker


class NoisyMarketSearch:
    def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
        if round_number == 1:
            return (
                SearchHit(
                    url="https://www.tradingview.com/symbols/ETHUSDC/",
                    title="ETHUSDC weekly price action",
                    snippet="ETHUSDC weekly analysis with price action, support, resistance, and seven day trend.",
                ),
                SearchHit(
                    url="https://example.test/physics",
                    title="Quantum field notes",
                    snippet="A physics explainer unrelated to crypto markets or digital asset price analysis.",
                ),
                SearchHit(
                    url="https://example.test/usdcad",
                    title="USDCAD weekly outlook",
                    snippet="USDCAD weekly price chart and FX trend outlook.",
                ),
                SearchHit(
                    url="https://pl.tradingview.com/symbols/ETHUSDC/technicals/",
                    title="ETHUSDC technicals",
                    snippet="TradingView technicals for ETHUSDC with momentum and trend summary.",
                ),
            )
        return (
            SearchHit(
                url="https://example.test/ethusdc-ohlcv",
                title="ETHUSDC OHLCV last week",
                snippet="OHLCV summary for ETHUSDC over the last week with daily high low and volume.",
            ),
            SearchHit(
                url="https://example.test/sociology",
                title="Social theory review",
                snippet="A sociology article with no market data and no ETHUSDC relevance.",
            ),
            SearchHit(
                url="https://www.tradingview.com/symbols/ETHUSDC.P/",
                title="ETHUSDC perpetual chart",
                snippet="TradingView perpetual chart for ETHUSDC with technical setup.",
            ),
        )


def test_research_job_manager_start_and_list_flow() -> None:
    persistence = create_in_memory_research_persistence()
    manager = ResearchJobManager(persistence)

    outcome = manager.start_job(
        ResearchJobStartRequest(owner_id="user-1", query="deep research architecture")
    )
    listed = manager.list_jobs("user-1")

    assert outcome.job.status is ResearchJobStatus.QUEUED
    assert outcome.job.problem_analysis is not None
    assert outcome.job.execution_plan is not None
    assert listed.jobs[0].job_id == outcome.job.job_id


def test_fake_research_worker_completes_job_and_persists_artifact() -> None:
    persistence, manager, worker = _build_test_execution()
    outcome = manager.start_job(
        ResearchJobStartRequest(owner_id="user-1", query="deep research architecture")
    )

    result = worker(outcome.job.job_id)
    status = manager.get_job_status(outcome.job.job_id)

    assert result is not None
    assert result.completion_mode is ResearchCompletionMode.FULL
    assert result.execution_plan is not None
    assert result.evidence_pack is not None
    assert status is not None
    assert status.job.status is ResearchJobStatus.DONE
    assert status.progress[-1].final is True
    compiled = persistence.compiled.get_artifact(f"cra-{outcome.job.job_id}")
    assert compiled is not None
    assert compiled.source_job_id == outcome.job.job_id
    assert compiled.owner_id == "user-1"
    lint = persistence.compiled_lint.get_lint_for_artifact(compiled.artifact_id)
    assert lint is not None
    assert lint.artifact_id == compiled.artifact_id


def test_fake_research_worker_can_save_partial_salvage_result() -> None:
    persistence, manager, worker = _build_test_execution()
    outcome = manager.start_job(
        ResearchJobStartRequest(owner_id="user-1", query="deep research architecture")
    )

    result = worker.save_partial_result(outcome.job.job_id)

    assert result is not None
    assert result.completion_mode is ResearchCompletionMode.PARTIAL_ERROR
    assert result.execution_plan is not None
    assert result.evidence_pack is not None
    assert manager.get_job_result(outcome.job.job_id).result is not None


def test_build_research_execution_wires_runtime_bundle() -> None:
    persistence, manager, worker = _build_test_execution()
    execution = type("Execution", (), {"start_job": manager.start_job, "get_job_status": manager.get_job_status, "cancel_job": manager.cancel_job, "get_job_result": manager.get_job_result, "list_jobs": manager.list_jobs, "run_job": worker})()
    accepted = execution.start_job(
        ResearchJobStartRequest(owner_id="user-1", query="deep research architecture")
    )
    status = execution.get_job_status(accepted.job.job_id)

    assert status is not None
    assert status.job.job_id == accepted.job.job_id


def test_fake_research_worker_runs_two_round_engine_loop() -> None:
    persistence, manager, worker = _build_test_execution()
    outcome = manager.start_job(
        ResearchJobStartRequest(owner_id="user-1", query="deep research architecture")
    )

    result = worker(outcome.job.job_id)
    status = manager.get_job_status(outcome.job.job_id)

    assert result is not None
    assert result.stats.rounds == 2
    assert result.stats.urls == 3
    assert len(result.raw_findings) == 3
    assert "## Current answer" in result.result
    assert "## Key findings" in result.result
    assert "## Uncertainty" in result.result
    assert "## Next checks" in result.result
    assert status is not None
    assert any(event.phase.value == "reading" for event in status.progress)
    assert any(event.phase.value == "analyzing" for event in status.progress)


def test_stub_query_generator_diversifies_market_queries_by_round() -> None:
    generator = StubQueryGenerator()
    round_one = generator(type("Plan", (), {"objective": "analiza ostatniego tygodnia ethusdc", "strategy": ResearchPlanStrategy.MARKET_SCAN})(), round_number=1)
    round_two = generator(type("Plan", (), {"objective": "analiza ostatniego tygodnia ethusdc", "strategy": ResearchPlanStrategy.MARKET_SCAN})(), round_number=2)

    assert any("price last 7 days" in query for query in round_one)
    assert any("technical analysis tradingview" in query for query in round_one)
    assert any("historical data" in query for query in round_two)
    assert any("exchange market" in query for query in round_two)
    assert any("analytics volume open interest" in query for query in round_two)


def test_stub_extractor_preserves_concrete_evidence_cues() -> None:
    extractor = StubExtractor()
    findings = extractor(
        (
            SearchHit(
                url="https://example.test/baseline",
                title="Configuration Baseline Evaluation",
                snippet="Clients report Compliant or Non-compliant after schedule evaluation; remediation can re-run checks every 7 days.",
            ),
        )
    )

    assert len(findings) == 1
    summary = findings[0].summary.lower()
    assert "key evidence:" in summary
    assert "compliant" in summary
    assert "non-compliant" in summary
    assert "schedule" in summary
    assert "7" in summary


def test_top_findings_prefers_source_type_diversity() -> None:
    findings = (
        ExtractedFinding(url="https://example.test/architecture", title="Architecture Guide", summary="General system design summary."),
        ExtractedFinding(url="https://example.test/chart", title="System Chart Analysis", summary="A longer analytical summary with shape and flow."),
        ExtractedFinding(url="https://example.test/market-data", title="Historical Data Export", summary="Concrete metrics and timeline values."),
        ExtractedFinding(url="https://example.test/notes", title="Operator Notes", summary="Generic operator observations."),
    )

    top = _top_findings(findings, limit=3)

    assert len(top) == 3
    titles = {finding.title for finding in top}
    assert "System Chart Analysis" in titles
    assert "Historical Data Export" in titles
    assert any(title in titles for title in ("Architecture Guide", "Operator Notes"))


def test_compile_research_artifact_projects_result_into_compiled_shape() -> None:
    persistence, manager, worker = _build_test_execution()
    outcome = manager.start_job(
        ResearchJobStartRequest(owner_id="user-1", query="how to deploy configuration baselines in sccm")
    )
    result = worker(outcome.job.job_id)

    assert result is not None
    compiled = _compile_research_artifact(result)
    assert compiled.title
    assert compiled.current_answer
    assert compiled.query == result.query
    assert compiled.problem_analysis_snapshot is not None
    assert compiled.execution_plan_snapshot is not None
    assert compiled.reflection_snapshot is not None
    assert compiled.evaluation_snapshot is not None
    assert compiled.source_refs or compiled.supporting_evidence
    assert compiled.next_checks or compiled.open_questions


def test_result_artifact_carries_evidence_pack_from_runtime_grouping() -> None:
    persistence, manager, worker = _build_test_execution()
    outcome = manager.start_job(
        ResearchJobStartRequest(owner_id="user-1", query="how to deploy configuration baselines in sccm")
    )
    result = worker(outcome.job.job_id)

    assert result is not None
    assert result.evidence_pack is not None
    assert result.branch_proposals is not None
    assert result.branch_evaluation is not None
    assert result.reflection is not None
    assert result.evidence_pack.pack_version == "evidence_pack_v1"
    assert result.evidence_pack.query_class is ResearchQueryClass.PROCEDURAL_ADMIN
    assert result.branch_proposals.eligible is False
    assert len(result.evidence_pack.core) + len(result.evidence_pack.supporting) + len(result.evidence_pack.background) >= 1


def test_research_report_prompt_overlay_for_procedural_admin_demands_operator_shape() -> None:
    overlay = _research_report_prompt_overlay(ResearchQueryClass.PROCEDURAL_ADMIN, has_direct_procedural_evidence=False)

    assert "exact admin path" in overlay
    assert "validation" in overlay
    assert "Do not invent wizard clicks" in overlay
    assert "Direct procedural evidence is not confirmed" in overlay


def test_build_research_report_prompt_includes_query_class_and_section_contract() -> None:
    prompt = _build_research_report_prompt(
        query="How to configure conditional access in Entra ID?",
        round_number=1,
        previous_answer="NONE",
        evidence="- Microsoft Learn: documented policy path.",
        query_class=ResearchQueryClass.PROCEDURAL_ADMIN,
        has_direct_procedural_evidence=False,
    )

    assert "Query class: procedural_admin" in prompt
    assert "Class-specific shaping rules:" in prompt
    assert "## Current answer" in prompt
    assert "## Next checks" in prompt
    assert "exact admin path or entry point" in prompt
    assert "Do not invent facts, steps, prerequisites, labels, paths, or recommendations." in prompt
    assert "say explicitly that you do not know or that the current evidence is insufficient" in prompt
    assert "Do not state exact click-paths, menu chains, field labels, or exact setup steps" in prompt


def test_llm_research_synthesizer_uses_prompt_builder_with_query_class_overlay() -> None:
    captured: dict[str, str] = {}

    def fake_synthesize_text(prompt: str):
        captured["prompt"] = prompt
        class _Result:
            text = "## Current answer\nUse Entra admin center path.\n\n## Key findings\n- Microsoft Learn documents the policy flow.\n\n## Uncertainty\n- Exact rollout safeguards need confirmation.\n\n## Next checks\n- Verify report-only guidance."
        return _Result()

    synth = LlmResearchSynthesizer(fake_synthesize_text)
    result = synth(
        query="How to configure conditional access in Entra ID?",
        round_number=1,
        findings=(
            ExtractedFinding(
                url="https://learn.microsoft.com/en-us/entra/identity/conditional-access/concept-conditional-access-policies",
                title="Build Conditional Access policies in Microsoft Entra",
                summary="Microsoft documents policy assignments, conditions, and controls.",
            ),
        ),
        previous_report=None,
    )

    prompt = captured["prompt"]
    assert "Query class: procedural_admin" in prompt
    assert "exact admin path or entry point" in prompt
    assert "Do not invent wizard clicks" in prompt
    assert ("Direct procedural evidence is not confirmed" in prompt) or ("Direct procedural evidence is present" in prompt)
    assert result.report_markdown.startswith("## Current answer")


def test_procedural_task_match_score_distinguishes_direct_task_from_adjacent_procedure() -> None:
    direct = _procedural_task_match_score(
        query="How to configure conditional access in Entra ID?",
        url="https://learn.microsoft.com/en-us/entra/identity/conditional-access/howto-conditional-access-policy-all-users-mfa",
        title="How to create a Conditional Access policy requiring MFA",
    )
    adjacent = _procedural_task_match_score(
        query="How to configure conditional access in Entra ID?",
        url="https://learn.microsoft.com/en-us/entra/identity/authentication/tutorial-enable-azure-mfa",
        title="Enable Microsoft Entra multifactor authentication - Microsoft Entra ID | Microsoft Learn",
    )

    assert direct > adjacent
    assert adjacent <= 1


def test_procedural_directness_score_prefers_task_pages_over_adjacent_context() -> None:
    direct = _procedural_directness_score(
        query="How to configure conditional access in Entra ID?",
        url="https://learn.microsoft.com/en-us/entra/identity/conditional-access/howto-conditional-access-policy-all-users-mfa",
        title="How to create a Conditional Access policy requiring MFA",
    )
    adjacent = _procedural_directness_score(
        query="How to configure conditional access in Entra ID?",
        url="https://learn.microsoft.com/sl-si/fabric/security/security-conditional-access",
        title="Conditional Access - Microsoft Fabric | Microsoft Learn",
    )
    conceptual = _procedural_directness_score(
        query="How to configure conditional access in Entra ID?",
        url="https://learn.microsoft.com/en-us/entra/identity/conditional-access/concept-conditional-access-conditions",
        title="Conditional Access: Conditions - Microsoft Entra ID",
    )
    adjacent_procedure = _procedural_directness_score(
        query="How to configure conditional access in Entra ID?",
        url="https://learn.microsoft.com/en-us/entra/identity/authentication/tutorial-enable-azure-mfa",
        title="Enable Microsoft Entra multifactor authentication - Microsoft Entra ID | Microsoft Learn",
    )

    assert direct > adjacent
    assert direct > conceptual
    assert direct > adjacent_procedure
    assert conceptual < direct


def test_procedural_overlay_allows_exactness_when_direct_evidence_exists() -> None:
    overlay = _research_report_prompt_overlay(ResearchQueryClass.PROCEDURAL_ADMIN, has_direct_procedural_evidence=True)

    assert "Direct procedural evidence is present" in overlay
    assert "may be stated only when they are supported by the evidence" in overlay


def test_top_findings_for_procedural_query_demotes_adjacent_official_context() -> None:
    findings = (
        ExtractedFinding(
            url="https://learn.microsoft.com/en-us/entra/identity/conditional-access/concept-conditional-access-conditions",
            title="Conditional Access: Conditions - Microsoft Entra ID",
            summary="Conceptual documentation for conditions.",
        ),
        ExtractedFinding(
            url="https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview",
            title="Microsoft Entra Conditional Access: Zero Trust Policy Engine",
            summary="Overview page.",
        ),
        ExtractedFinding(
            url="https://learn.microsoft.com/sl-si/fabric/security/security-conditional-access",
            title="Conditional Access - Microsoft Fabric | Microsoft Learn",
            summary="Adjacent service context.",
        ),
        ExtractedFinding(
            url="https://learn.microsoft.com/en-us/entra/identity/conditional-access/howto-conditional-access-policy-all-users-mfa",
            title="How to create a Conditional Access policy requiring MFA",
            summary="Direct setup guidance.",
        ),
    )

    ranked = _top_findings(findings, query="How to configure conditional access in Entra ID?", limit=4)

    assert ranked[0].title == "How to create a Conditional Access policy requiring MFA"
    assert ranked.index(next(item for item in ranked if item.title == "Conditional Access - Microsoft Fabric | Microsoft Learn")) > 0
    assert ranked.index(next(item for item in ranked if item.title == "Conditional Access: Conditions - Microsoft Entra ID")) > 0


def test_lint_compiled_research_artifact_flags_snapshot_and_reflection_followup_gaps() -> None:
    artifact = CompiledResearchArtifact(
        artifact_id="cra-1",
        source_job_id="rj-1",
        owner_id="user-1",
        query="test query",
        query_class=ResearchQueryClass.BROAD_CONCEPT,
        title="Test",
        summary="Summary",
        current_answer="Answer",
        supporting_evidence=(CompiledResearchEvidenceRef(url="https://example.test", title="Example", summary="Summary"),),
        source_refs=(ResearchSource(url="https://example.test", title="Example"),),
        problem_analysis_snapshot=ProblemAnalysis(
            query_class=ResearchQueryClass.BROAD_CONCEPT,
            complexity=ResearchComplexity.HIGH,
            goal="test query",
        ),
        execution_plan_snapshot=ResearchExecutionPlan(
            strategy=ResearchPlanStrategy.BROAD_RESEARCH,
            objective="test query",
            steps=(ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Collect sources."),),
        ),
        reflection_snapshot=ResearchReflection(
            goal_coverage="weak",
            should_follow_up=True,
            recommended_follow_up=None,
        ),
        evaluation_snapshot=ResearchEvaluationArtifact(
            query_class=ResearchQueryClass.BROAD_CONCEPT,
            should_revise_report=False,
        ),
        created_at="2026-06-21T00:00:00+00:00",
    )

    lint = _lint_compiled_research_artifact(artifact)

    assert 'shallow_execution_plan_snapshot' in lint.risk_flags
    assert 'reflection_followup_without_next_checks' in lint.risk_flags
    assert 'weak_reflection_without_guidance' in lint.risk_flags
    assert 'reflection_evaluation_mismatch' in lint.risk_flags
    assert lint.status is CompiledResearchArtifactLintStatus.WEAK


def test_lint_compiled_research_artifact_flags_open_questions_without_next_checks() -> None:
    artifact = CompiledResearchArtifact(
        artifact_id="cra-1",
        source_job_id="rj-1",
        owner_id="user-1",
        query="test query",
        query_class=ResearchQueryClass.BROAD_CONCEPT,
        title="Test",
        summary="Summary",
        current_answer="Answer",
        supporting_evidence=(),
        open_questions=("What changed?",),
        next_checks=(),
        source_refs=(ResearchSource(url="https://example.test", title="Example"),),
        evaluation_snapshot=ResearchEvaluationArtifact(
            query_class=ResearchQueryClass.BROAD_CONCEPT,
            source_quality_verdict=ResearchEvaluationVerdict.MIXED,
            truthfulness_verdict=ResearchEvaluationVerdict.MIXED,
        ),
        created_at="2026-06-21T00:00:00+00:00",
    )

    lint = _lint_compiled_research_artifact(artifact)

    assert lint.status is CompiledResearchArtifactLintStatus.WEAK
    assert "open_questions_without_next_checks" in lint.risk_flags
    assert lint.recommended_next_action == "revise_artifact"


def test_enriched_compiled_artifact_improves_lint_surface() -> None:
    persistence, manager, worker = _build_test_execution()
    outcome = manager.start_job(
        ResearchJobStartRequest(owner_id="user-1", query="how to deploy configuration baselines in sccm")
    )
    result = worker(outcome.job.job_id)

    assert result is not None
    compiled = _compile_research_artifact(result)
    lint = _lint_compiled_research_artifact(compiled)

    assert compiled.source_refs
    assert compiled.next_checks or compiled.open_questions
    assert lint.recommended_next_action in {"review_artifact", "artifact_ready", "revise_artifact"}


def test_project_supporting_evidence_falls_back_to_report_key_findings() -> None:
    result = type("Result", (), {
        "job_id": "rj-1",
        "raw_findings": (),
        "sources": (),
        "result": "## Current answer\nUseful answer\n\n## Key findings\n- First report finding\n- Second report finding\n",
    })()

    evidence = _compile_research_artifact(
        ResearchResultArtifact(
            job_id="rj-1",
            owner_id="user-1",
            query="test query",
            status=ResearchJobStatus.DONE,
            completion_mode=ResearchCompletionMode.FULL,
            result=result.result,
            raw_report=result.result,
            created_at="2026-06-21T00:00:00+00:00",
        )
    ).supporting_evidence

    assert evidence
    assert evidence[0].url.startswith("about:report/rj-1#key-findings-")


def test_procedural_admin_unified_search_adapter_prefers_unified_hits_for_procedural_queries() -> None:
    current = build_search_adapter(search_web=lambda query, count=3: [
        {'url': 'https://example.test/blog', 'title': 'Blog', 'snippet': 'Generic result'}
    ])
    unified = build_procedural_admin_unified_search_adapter(
        current_search=current,
        unified_search_web=lambda query, count=10: [
            {
                'url': 'https://learn.microsoft.com/en-us/intune/configmgr/compliance/deploy-use/create-configuration-baselines',
                'title': 'Create configuration baselines - Configuration Manager | Microsoft Learn',
                'snippet': 'Official Microsoft Learn documentation.',
            }
        ],
    )

    hits = unified(("How do I create configuration baselines in SCCM?",), round_number=1)

    assert hits
    assert hits[0].url.startswith('https://learn.microsoft.com/')


def test_procedural_admin_unified_search_adapter_falls_back_when_unified_hits_lack_official_docs() -> None:
    current = build_search_adapter(search_web=lambda query, count=3: [
        {'url': 'https://learn.microsoft.com/en-us/intune/configmgr/compliance/deploy-use/create-configuration-baselines', 'title': 'Create configuration baselines - Configuration Manager | Microsoft Learn', 'snippet': 'Official docs'}
    ])
    unified = build_procedural_admin_unified_search_adapter(
        current_search=current,
        unified_search_web=lambda query, count=10: [
            {'url': 'https://www.youtube.com/watch?v=123', 'title': 'YouTube tutorial', 'snippet': 'Video result'},
            {'url': 'https://www.reddit.com/r/SCCM/comments/x', 'title': 'Reddit thread', 'snippet': 'Forum result'},
        ],
    )

    hits = unified(("How do I create configuration baselines in SCCM?",), round_number=1)

    assert hits
    assert hits[0].url.startswith('https://learn.microsoft.com/')


def test_general_relevance_prefers_procedural_docs_over_loose_noise() -> None:
    query = "jak działa configuration baseline w sccm po wdrożeniu na kolekcję komputerów"
    strong_hit = SearchHit(
        url="https://learn.microsoft.com/en-us/intune/configmgr/compliance/deploy-use/create-configuration-baselines",
        title="Create configuration baselines - Configuration Manager | Microsoft Learn",
        snippet="Learn how configuration baselines are created and deployed in Configuration Manager.",
    )
    weak_hit = SearchHit(
        url="https://w-files.pl/category/security/",
        title="security – W-Files",
        snippet="Category page with mixed security articles.",
    )

    assert _is_relevant_hit(query=query, hit=strong_hit) is True
    assert _looks_like_listing_page(weak_hit) is True
    assert _is_relevant_hit(query=query, hit=weak_hit) is False


def test_fake_research_worker_filters_off_topic_hits_for_market_query() -> None:
    persistence = create_in_memory_research_persistence()
    manager = ResearchJobManager(persistence)
    worker = FakeResearchWorker(persistence, search=NoisyMarketSearch())
    outcome = manager.start_job(
        ResearchJobStartRequest(owner_id="user-1", query="analiza ostatniego tygodnia ethusdc")
    )

    result = worker(outcome.job.job_id)

    assert result is not None
    assert result.problem_analysis is not None
    assert result.execution_plan is not None
    assert result.problem_analysis.goal == outcome.job.query
    assert result.execution_plan.objective == outcome.job.query
    assert result.stats.rounds == 2
    assert len(result.sources) == 3
    assert all("ethusdc" in source.title.lower() or "ethusdc" in source.url.lower() for source in result.sources)
    assert all("usdcad" not in source.title.lower() and "usdcad" not in source.url.lower() for source in result.sources)
    tradingview_sources = [source for source in result.sources if "tradingview.com" in source.url]
    assert len(tradingview_sources) == 2
    assert any("example.test" in source.url for source in result.sources)
    assert "physics" not in result.result.lower()
    assert "sociology" not in result.result.lower()
    assert "usdcad" not in result.result.lower()


def test_evidence_packing_prefers_official_docs_as_core_for_procedural_query() -> None:
    findings = (
        ExtractedFinding(
            url="https://learn.microsoft.com/en-us/intune/configmgr/compliance/deploy-use/create-configuration-baselines",
            title="Create configuration baselines - Configuration Manager | Microsoft Learn",
            summary="Official procedural documentation.",
        ),
        ExtractedFinding(
            url="https://learn.microsoft.com/en-us/intune/configmgr/compliance/deploy-use/deploy-configuration-baselines",
            title="Deploy configuration baselines - Configuration Manager | Microsoft Learn",
            summary="Deployment guidance for baselines.",
        ),
        ExtractedFinding(
            url="https://www.velessoftware.com/blog/deploy-a-sccm-configuration-baseline",
            title="Deploy a SCCM Configuration Baseline",
            summary="Community blog walkthrough.",
        ),
        ExtractedFinding(
            url="https://learn.microsoft.com/en-us/intune/configmgr/compliance/get-started/get-started-with-compliance-settings",
            title="Get started with compliance settings",
            summary="Broader compliance settings overview.",
        ),
    )

    packed = _pack_evidence_for_synthesis(
        query='How do I create configuration baselines in SCCM?',
        findings=findings,
    )

    assert len(packed.core) >= 1
    assert all('learn.microsoft.com' in finding.url for finding in packed.core)
    assert all('velessoftware.com' not in finding.url for finding in packed.core)
    assert len(packed.background) >= 1
    assert packed.has_direct_procedural_evidence is True


def test_problem_analysis_derivation_for_broad_and_procedural_queries() -> None:
    broad = _derive_problem_analysis("deep research architecture")
    procedural = _derive_problem_analysis("How do I create configuration baselines in SCCM?")

    assert broad.query_class is ResearchQueryClass.BROAD_CONCEPT
    assert broad.complexity is ResearchComplexity.HIGH
    assert "system_shape" in broad.focus_areas
    assert procedural.query_class is ResearchQueryClass.PROCEDURAL_ADMIN
    assert procedural.complexity is ResearchComplexity.LOW
    assert "validation" in procedural.focus_areas
    assert "state_exact_steps_only_when_supported_by_evidence" in procedural.constraints


def test_branch_proposals_are_only_eligible_for_broad_or_high_complexity_queries() -> None:
    broad_analysis = ProblemAnalysis(
        query_class=ResearchQueryClass.BROAD_CONCEPT,
        complexity=ResearchComplexity.HIGH,
        goal="deep research architecture",
    )
    procedural_analysis = ProblemAnalysis(
        query_class=ResearchQueryClass.PROCEDURAL_ADMIN,
        complexity=ResearchComplexity.LOW,
        goal="How do I create configuration baselines in SCCM?",
    )
    broad_plan = ResearchExecutionPlan(
        strategy=ResearchPlanStrategy.BROAD_RESEARCH,
        objective="deep research architecture",
        steps=(ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Collect high-signal conceptual and technical sources."),),
    )

    broad = _derive_branch_proposals(problem_analysis=broad_analysis, execution_plan=broad_plan)
    procedural = _derive_branch_proposals(problem_analysis=procedural_analysis, execution_plan=None)

    assert broad.eligible is True
    assert broad.reason == "broad_or_high_complexity_query"
    assert len(broad.branches) == 3
    assert procedural.eligible is False
    assert procedural.reason == "query_not_eligible"
    assert procedural.branches == ()


def test_branch_evaluator_selects_top_two_branches_for_eligible_broad_query() -> None:
    analysis = ProblemAnalysis(
        query_class=ResearchQueryClass.BROAD_CONCEPT,
        complexity=ResearchComplexity.HIGH,
        goal="deep research architecture",
        focus_areas=("definition", "system_shape", "key_tradeoffs"),
    )
    plan = ResearchExecutionPlan(
        strategy=ResearchPlanStrategy.BROAD_RESEARCH,
        objective="deep research architecture",
        steps=(
            ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Collect sources."),
            ResearchExecutionPlanStep(step_id="step-2", kind="analyze", objective="Analyze tradeoffs.", depends_on=("step-1",)),
        ),
    )
    proposals = _derive_branch_proposals(problem_analysis=analysis, execution_plan=plan)
    evidence_pack = ResearchEvidencePack(
        query_class=ResearchQueryClass.BROAD_CONCEPT,
        core=(ResearchFinding(url="https://example.test/1", title="A", summary="Summary A"), ResearchFinding(url="https://example.test/2", title="B", summary="Summary B")),
        supporting=(ResearchFinding(url="https://example.test/3", title="C", summary="Summary C"),),
    )

    evaluation = _evaluate_branch_proposals(
        problem_analysis=analysis,
        execution_plan=plan,
        evidence_pack=evidence_pack,
        branch_proposals=proposals,
    )

    assert evaluation.evaluation_version == "branch_evaluator_v1"
    assert len(evaluation.scores) == 3
    assert len(evaluation.selected_branch_ids) <= 2
    assert evaluation.selected_branch_ids[0] == evaluation.scores[0].branch_id


def test_reflection_emits_bounded_follow_up_for_thin_broad_result() -> None:
    analysis = ProblemAnalysis(
        query_class=ResearchQueryClass.BROAD_CONCEPT,
        complexity=ResearchComplexity.HIGH,
        goal="deep research architecture",
        focus_areas=("definition", "system_shape", "key_tradeoffs"),
    )
    plan = ResearchExecutionPlan(
        strategy=ResearchPlanStrategy.BROAD_RESEARCH,
        objective="deep research architecture",
        steps=(ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Collect sources."),),
    )
    evidence_pack = ResearchEvidencePack(
        query_class=ResearchQueryClass.BROAD_CONCEPT,
        core=(ResearchFinding(url="https://example.test/1", title="A", summary="Summary A"),),
        supporting=(),
    )
    branch_evaluation = ResearchBranchEvaluation(selected_branch_ids=("branch-1",))
    evaluation = ResearchEvaluationArtifact(
        query_class=ResearchQueryClass.BROAD_CONCEPT,
        relevance_verdict=ResearchEvaluationVerdict.MIXED,
    )

    reflection = _derive_reflection(
        problem_analysis=analysis,
        execution_plan=plan,
        evidence_pack=evidence_pack,
        branch_evaluation=branch_evaluation,
        evaluation=evaluation,
    )

    assert reflection.reflection_version == "reflection_v1"
    assert reflection.goal_coverage in {"partial", "weak"}
    assert reflection.should_follow_up is True
    assert reflection.recommended_follow_up is not None


def test_stub_planner_uses_problem_analysis_to_build_execution_plan() -> None:
    problem_analysis = ProblemAnalysis(
        query_class=ResearchQueryClass.PROCEDURAL_ADMIN,
        complexity=ResearchComplexity.LOW,
        goal="How do I create configuration baselines in SCCM?",
        focus_areas=("task_path", "required_controls", "validation"),
        constraints=("state_exact_steps_only_when_supported_by_evidence",),
    )
    from sourcetrace.application.research_runtime import StubResearchPlanner
    plan = StubResearchPlanner()(problem_analysis.goal, problem_analysis=problem_analysis)

    assert plan.strategy is ResearchPlanStrategy.PROCEDURAL_RESEARCH
    assert plan.objective == problem_analysis.goal
    assert len(plan.steps) == 3
    assert plan.steps[0].kind == "search"
    assert plan.steps[-1].depends_on == ("step-2",)


def test_query_classification_and_post_result_evaluator_for_procedural_query() -> None:
    query = "How do I create configuration baselines in SCCM?"
    findings = (
        ResearchFinding(
            url="https://learn.microsoft.com/en-us/intune/configmgr/compliance/deploy-use/create-configuration-baselines",
            title="Create configuration baselines - Configuration Manager | Microsoft Learn",
            summary="Official procedural documentation.",
        ),
        ResearchFinding(
            url="https://www.velessoftware.com/blog/deploy-a-sccm-configuration-baseline",
            title="Deploy a SCCM Configuration Baseline",
            summary="Community blog walkthrough.",
        ),
    )
    report = "## Current answer\nUse Microsoft Learn guidance.\n\n## Key findings\n- Official docs are present.\n\n## Uncertainty\n- Community material still appears.\n\n## Next checks\n- Verify exact wizard options on Microsoft Learn."

    assert _classify_query(query) is ResearchQueryClass.PROCEDURAL_ADMIN
    evaluation = _evaluate_research_result(
        query=query,
        findings=findings,
        report=report,
        stats=ResearchStats(search_providers=("searxng",)),
    )

    assert evaluation.query_class is ResearchQueryClass.PROCEDURAL_ADMIN
    assert evaluation.source_quality_verdict is ResearchEvaluationVerdict.MIXED
    assert evaluation.relevance_verdict is ResearchEvaluationVerdict.STRONG
    assert evaluation.truthfulness_verdict is ResearchEvaluationVerdict.MIXED
    assert evaluation.should_revise_report is False


def test_procedural_task_match_preserves_matching_adjacent_page_for_matching_query() -> None:
    match_score = _procedural_task_match_score(
        query="How to enable Microsoft Entra multifactor authentication?",
        url="https://learn.microsoft.com/en-us/entra/identity/authentication/tutorial-enable-azure-mfa",
        title="Enable Microsoft Entra multifactor authentication - Microsoft Entra ID | Microsoft Learn",
    )
    direct_score = _procedural_directness_score(
        query="How to enable Microsoft Entra multifactor authentication?",
        url="https://learn.microsoft.com/en-us/entra/identity/authentication/tutorial-enable-azure-mfa",
        title="Enable Microsoft Entra multifactor authentication - Microsoft Entra ID | Microsoft Learn",
    )

    assert match_score >= 2
    assert direct_score >= 3


def test_procedural_vendor_and_social_sources_are_demoted_when_official_docs_exist() -> None:
    findings = (
        ExtractedFinding(
            url="https://learn.microsoft.com/en-us/entra/identity/conditional-access/policy-alt-all-users-compliant-hybrid-or-mfa",
            title="Require compliant, hybrid joined devices, or MFA - Microsoft Entra ID",
            summary="Official direct task guidance.",
        ),
        ExtractedFinding(
            url="https://www.manageengine.com/microsoft-365-management-reporting/kb/how-to-configure-conditional-access-in-microsoft-entra-id.html",
            title="How to configure Conditional Access in Microsoft Entra ID",
            summary="Vendor KB article.",
        ),
        ExtractedFinding(
            url="https://www.linkedin.com/pulse/locking-down-conditional-access-policies-lesson-entra-manish-periwal-yqnxe",
            title="Locking Down Conditional Access Policies: A Lesson in Entra",
            summary="LinkedIn post.",
        ),
    )

    ranked = _top_findings(findings, query="How to configure conditional access in Entra ID?", limit=3)

    assert ranked[0].url.startswith("https://learn.microsoft.com/")
    assert any("manageengine.com" in item.url for item in ranked[1:])
    assert all("linkedin.com" not in item.url for item in ranked)


def test_project_source_refs_for_procedural_query_prefers_official_docs_in_persisted_sources() -> None:
    result = ResearchResultArtifact(
        job_id="rj-1",
        owner_id="user-1",
        query="How to configure conditional access in Entra ID?",
        status=ResearchJobStatus.DONE,
        completion_mode=ResearchCompletionMode.FULL,
        result="## Current answer\nUse official documentation.\n\n## Key findings\n- Official docs exist.\n\n## Uncertainty\n- None.\n\n## Next checks\n- None.",
        raw_report="",
        stats=ResearchStats(search_providers=("procedural_admin_unified_search", "searxng")),
        execution_plan=ResearchExecutionPlan(
            strategy=ResearchPlanStrategy.PROCEDURAL_RESEARCH,
            objective="How to configure conditional access in Entra ID?",
            steps=(ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Find direct procedural or official task guidance."),),
        ),
        evidence_pack=ResearchEvidencePack(query_class=ResearchQueryClass.PROCEDURAL_ADMIN),
        sources=(
            ResearchSource(url="https://www.manageengine.com/microsoft-365-management-reporting/kb/how-to-configure-conditional-access-in-microsoft-entra-id.html", title="ManageEngine KB"),
            ResearchSource(url="https://learn.microsoft.com/en-us/entra/identity/conditional-access/policy-alt-all-users-compliant-hybrid-or-mfa", title="Require compliant, hybrid joined devices, or MFA - Microsoft Entra ID"),
            ResearchSource(url="https://www.linkedin.com/pulse/locking-down-conditional-access-policies-lesson-entra-manish-periwal-yqnxe", title="LinkedIn post"),
            ResearchSource(url="https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview", title="Microsoft Entra Conditional Access: Zero Trust Policy Engine"),
        ),
        raw_findings=(
            ResearchFinding(url="https://learn.microsoft.com/en-us/entra/identity/conditional-access/policy-alt-all-users-compliant-hybrid-or-mfa", title="Require compliant, hybrid joined devices, or MFA - Microsoft Entra ID", summary="Official direct task guidance."),
        ),
    )

    projected = _project_source_refs(result, ())

    assert projected
    assert projected[0].url.startswith("https://learn.microsoft.com/")


def test_file_backed_research_persistence_roundtrips_new_artifact_fields(tmp_path) -> None:
    persistence = create_file_backed_research_persistence(tmp_path)
    manager = ResearchJobManager(persistence)
    worker = FakeResearchWorker(persistence, search=DeterministicSearch())

    outcome = manager.start_job(
        ResearchJobStartRequest(owner_id="user-1", query="deep research architecture")
    )
    result = worker(outcome.job.job_id)

    reloaded = create_file_backed_research_persistence(tmp_path)
    job = reloaded.jobs.get_job(outcome.job.job_id)
    persisted_result = reloaded.results.get_result(outcome.job.job_id)
    compiled = reloaded.compiled.get_artifact(f"cra-{outcome.job.job_id}")
    lint = reloaded.compiled_lint.get_lint_for_artifact(f"cra-{outcome.job.job_id}")

    assert result.problem_analysis is not None
    assert job is not None and job.problem_analysis is not None
    assert job.execution_plan is not None
    assert persisted_result is not None and persisted_result.problem_analysis is not None
    assert persisted_result.execution_plan is not None
    assert persisted_result.evidence_pack is not None
    assert persisted_result.branch_proposals is not None
    assert persisted_result.branch_evaluation is not None
    assert persisted_result.reflection is not None
    assert compiled is not None and compiled.problem_analysis_snapshot is not None
    assert compiled.execution_plan_snapshot is not None
    assert compiled.reflection_snapshot is not None
    assert lint is not None


def test_general_query_class_replaces_unknown_for_broad_nonprocedural_question() -> None:
    analysis = _derive_problem_analysis("Wpływ pracy zdalnej na zdrowie psychiczne pracowników po 2023 roku")

    assert analysis.query_class is ResearchQueryClass.GENERAL
    assert analysis.complexity is ResearchComplexity.MEDIUM


def test_evidence_pack_uses_supporting_for_general_query_with_nonempty_findings() -> None:
    findings = (
        ExtractedFinding(
            url="https://example.org/report",
            title="Remote work and mental health report",
            summary="Summary about the impact of remote work on employee mental health.",
        ),
    )

    packed = _pack_evidence_for_synthesis(
        query="Wpływ pracy zdalnej na zdrowie psychiczne pracowników po 2023 roku",
        findings=findings,
    )

    assert len(packed.core) == 0
    assert len(packed.supporting) == 1


def test_lint_flags_thin_evidence_base_when_reflection_reports_no_core_evidence() -> None:
    artifact = CompiledResearchArtifact(
        artifact_id="cra-thin",
        source_job_id="rj-thin",
        owner_id="user-1",
        query="General research query",
        query_class=ResearchQueryClass.GENERAL,
        title="Thin artifact",
        summary="Summary",
        current_answer="Answer",
        key_claims=(CompiledResearchClaim(text="Claim", evidence_refs=("https://example.org/report",)),),
        supporting_evidence=(),
        source_refs=(ResearchSource(url="https://example.org/report", title="Example"),),
        reflection_snapshot=ResearchReflection(
            goal_coverage="partial",
            weak_evidence_areas=("no_core_evidence",),
            should_follow_up=True,
            recommended_follow_up="Gather stronger evidence.",
        ),
        evaluation_snapshot=ResearchEvaluationArtifact(query_class=ResearchQueryClass.GENERAL),
        created_at="2026-06-24T00:00:00+00:00",
    )

    lint = _lint_compiled_research_artifact(artifact)

    assert 'thin_evidence_base' in lint.risk_flags
    assert 'claims_without_supporting_evidence' in lint.risk_flags
    assert lint.recommended_next_action == 'revise_artifact'


def test_file_backed_payload_load_maps_legacy_unknown_query_class_to_general() -> None:
    from sourcetrace.storage.research_filesystem import _problem_analysis_from_payload

    analysis = _problem_analysis_from_payload({
        "query_class": "unknown",
        "complexity": "medium",
        "goal": "legacy question",
    })

    assert analysis is not None
    assert analysis.query_class is ResearchQueryClass.GENERAL


def test_pack_evidence_for_general_query_preserves_supporting_from_cumulative_findings() -> None:
    findings = (
        ExtractedFinding(
            url="https://example.org/report-1",
            title="Remote work and mental health report",
            summary="Evidence summary one.",
        ),
        ExtractedFinding(
            url="https://example.org/report-2",
            title="Follow-up remote work analysis",
            summary="Evidence summary two.",
        ),
    )

    packed = _pack_evidence_for_synthesis(
        query="Wpływ pracy zdalnej na zdrowie psychiczne pracowników po 2023 roku",
        findings=findings,
    )
    evidence_pack = _to_research_evidence_pack(
        query="Wpływ pracy zdalnej na zdrowie psychiczne pracowników po 2023 roku",
        packed=packed,
    )

    assert evidence_pack.query_class is ResearchQueryClass.GENERAL
    assert len(evidence_pack.core) == 0
    assert len(evidence_pack.supporting) >= 1


def test_stub_query_generator_expands_direct_answer_queries_after_first_round() -> None:
    generator = StubQueryGenerator()
    plan = ResearchExecutionPlan(
        strategy=ResearchPlanStrategy.DIRECT_ANSWER,
        objective="Wpływ pracy zdalnej na zdrowie psychiczne pracowników po 2023 roku",
        steps=(ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Gather evidence."),),
    )

    first_round = generator(plan, round_number=1)
    second_round = generator(plan, round_number=2)

    assert first_round == ("Wpływ pracy zdalnej na zdrowie psychiczne pracowników po 2023 roku",)
    assert len(second_round) == 3
    assert any("report study" in query for query in second_round)


def test_general_relevance_retains_nonprocedural_analysis_hit_with_strong_context() -> None:
    hit = SearchHit(
        url="https://example.org/remote-work-mental-health-analysis",
        title="Remote work mental health analysis after 2023",
        snippet="Detailed research findings and survey evidence about employee mental health in remote work.",
    )

    assert _is_relevant_hit(
        query="Wpływ pracy zdalnej na zdrowie psychiczne pracowników po 2023 roku",
        hit=hit,
    ) is True


def test_searxng_adapter_uses_higher_per_query_count_after_first_round() -> None:
    adapter = SearxNGSearchAdapter(base_url="http://example.test", count=3)

    seen_counts: list[int] = []

    def fake_fetch(query: str, *, count: int | None = None) -> list[dict[str, object]]:
        seen_counts.append(count or 0)
        return [
            {"url": f"https://example.test/{i}", "title": f"Result {i}", "snippet": "Snippet"}
            for i in range(count or 0)
        ]

    adapter._fetch = fake_fetch  # type: ignore[method-assign]

    round_one = adapter(("query",), round_number=1)
    round_two = adapter(("query",), round_number=2)

    assert len(round_one) == 3
    assert len(round_two) == 6
    assert seen_counts == [3, 6]


def test_search_rejection_summary_reports_duplicate_and_low_relevance_counts() -> None:
    existing = [SearchHit(url="https://example.org/a", title="A", snippet="")]
    candidates = (
        SearchHit(url="https://example.org/a", title="A", snippet=""),
        SearchHit(url="https://example.org/b", title="Unrelated", snippet="Nothing relevant here"),
        SearchHit(url="https://example.org/c", title="Remote work mental health analysis 2024", snippet="Research findings"),
    )

    summary = _search_rejection_summary(
        query="Wpływ pracy zdalnej na zdrowie psychiczne pracowników po 2023 roku",
        existing_hits=existing,
        candidate_hits=candidates,
    )

    assert 'accepted=' in summary
    assert 'duplicate=1' in summary


def test_general_relevance_retains_context_rich_hit_even_with_limited_keyword_overlap() -> None:
    hit = SearchHit(
        url="https://example.org/workplace-wellbeing-study",
        title="Workplace wellbeing study on distributed workforces after 2023",
        snippet="Long-form research summary covering employee stress, isolation, wellbeing outcomes, and survey findings across remote and hybrid work settings.",
    )

    assert _is_relevant_hit(
        query="Wpływ pracy zdalnej na zdrowie psychiczne pracowników po 2023 roku",
        hit=hit,
    ) is True


def test_general_evidence_pack_allows_up_to_three_supporting_findings() -> None:
    findings = tuple(
        ExtractedFinding(
            url=f"https://example.org/report-{i}",
            title=f"Remote work mental health report {i}",
            summary=f"Evidence summary {i} about remote work and mental health after 2023.",
        )
        for i in range(1, 5)
    )

    packed = _pack_evidence_for_synthesis(
        query="Wpływ pracy zdalnej na zdrowie psychiczne pracowników po 2023 roku",
        findings=findings,
    )

    assert len(packed.core) == 0
    assert len(packed.supporting) == 3
