from sourcetrace.application import (
    ExtractedFinding,
    FakeResearchWorker,
    ResearchJobManager,
    ResearchJobStartRequest,
    StubExtractor,
    StubQueryGenerator,
    SearchHit,
)
from sourcetrace.application.research_runtime import (
    LlmResearchSynthesizer,
    ResearchSearchError,
    StubQueryGenerator,
    _authority_signal_score,
    _build_research_report_prompt,
    _classify_query,
    _compile_research_artifact,
    _evaluate_research_result,
    _filter_hits_for_extraction,
    _is_relevant_hit,
    _lint_compiled_research_artifact,
    _looks_like_listing_page,
    _pack_evidence_for_synthesis,
    _procedural_query_bias,
    _project_source_refs,
    _procedural_directness_score,
    _procedural_task_match_score,
    _procedural_query_variants,
    _research_report_prompt_overlay,
    _top_findings,
    build_procedural_admin_unified_search_adapter,
    build_search_adapter,
)
from sourcetrace.domain import (
    CompiledResearchArtifact,
    CompiledResearchArtifactLintStatus,
    ResearchCompletionMode,
    ResearchEvaluationArtifact,
    ResearchEvaluationVerdict,
    ResearchFinding,
    ResearchJobStatus,
    ResearchQueryClass,
    ResearchResultArtifact,
    ResearchSource,
    ResearchStats,
)
from sourcetrace.storage import create_in_memory_research_persistence


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
    round_one = generator(type("Plan", (), {"objective": "analiza ostatniego tygodnia ethusdc"})(), round_number=1)
    round_two = generator(type("Plan", (), {"objective": "analiza ostatniego tygodnia ethusdc"})(), round_number=2)

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
    assert compiled.evaluation_snapshot is not None
    assert compiled.source_refs or compiled.supporting_evidence
    assert compiled.next_checks or compiled.open_questions


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
    assert all("linkedin.com" not in item.url for item in projected)
    assert all("manageengine.com" not in item.url for item in projected)
    assert projected[0].url.startswith("https://learn.microsoft.com/")


def test_procedural_evaluator_downgrades_indirect_official_context() -> None:
    query = "How to configure a policy in an admin portal?"
    findings = (
        ResearchFinding(
            url="https://learn.microsoft.com/en-us/product/overview",
            title="Policy engine overview",
            summary="Official overview page describing policy concepts.",
        ),
        ResearchFinding(
            url="https://learn.microsoft.com/en-us/product/concept-conditions",
            title="Conditions concept",
            summary="Official concept page for conditions and controls.",
        ),
    )
    report = "## Current answer\nUse the admin portal to configure the policy.\n\n## Key findings\n- Official docs describe policy concepts.\n\n## Uncertainty\n- Exact setup steps are not confirmed.\n\n## Next checks\n- Find the direct setup page."

    evaluation = _evaluate_research_result(
        query=query,
        findings=findings,
        report=report,
        stats=ResearchStats(search_providers=("searxng",), authority_policy_applied=True),
    )

    assert evaluation.source_quality_verdict is ResearchEvaluationVerdict.MIXED
    assert evaluation.relevance_verdict is ResearchEvaluationVerdict.MIXED
    assert evaluation.truthfulness_verdict is ResearchEvaluationVerdict.MIXED
    assert any("direct task/setup evidence is not confirmed" in reason for reason in evaluation.source_quality_reasons)
    assert any("indirect procedural context" in risk for risk in evaluation.relevance_risks)
    assert any("Find at least one direct task or setup page" in check for check in evaluation.missing_checks)
    assert any("Official documentation" in reason for reason in evaluation.source_quality_reasons)


def test_chained_search_adapter_falls_back_after_empty_or_soft_failure() -> None:
    from sourcetrace.application.research_runtime import (
        ChainedSearchAdapter,
        ResearchSearchError,
        SearchProviderBridge,
        SearxNGSearchAdapter,
        build_provider_search_adapter,
    )

    class EmptyAdapter:
        def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
            return ()

    class FailingAdapter:
        def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
            raise ResearchSearchError('searx temporary failure')

    class ProviderAdapter:
        def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
            return (
                SearchHit(
                    url='https://example.test/fallback',
                    title='Fallback Result',
                    snippet='Recovered via provider fallback.',
                ),
            )

    chained = ChainedSearchAdapter(EmptyAdapter(), ProviderAdapter())
    hits = chained(('query',), round_number=1)
    assert len(hits) == 1
    assert hits[0].title == 'Fallback Result'

    chained_after_error = ChainedSearchAdapter(FailingAdapter(), ProviderAdapter())
    hits_after_error = chained_after_error(('query',), round_number=1)
    assert len(hits_after_error) == 1
    assert hits_after_error[0].url == 'https://example.test/fallback'

    adapter = build_provider_search_adapter(
        searxng_base_url='http://127.0.0.1:18080',
        search_web=lambda query, count=3: [{'url': 'https://example.test/provider', 'title': 'Provider Result', 'snippet': 'Provider snippet'}],
        bridge=SearchProviderBridge(),
    )
    assert isinstance(adapter, ChainedSearchAdapter)


def test_procedural_query_bias_does_not_treat_generic_gaming_howto_as_admin_query() -> None:
    assert _procedural_query_bias("how do I deploy configuration baselines in SCCM") is True
    assert _procedural_query_bias("what are important elements for poe2 monk to be able do endgame") is False


def test_build_search_adapter_raises_when_no_provider_is_configured() -> None:
    try:
        build_search_adapter()
    except ResearchSearchError as exc:
        assert "Search is unavailable" in str(exc)
    else:
        raise AssertionError("Expected ResearchSearchError when no search backend is configured")


def test_fake_research_worker_errors_when_search_returns_no_results() -> None:
    persistence = create_in_memory_research_persistence()
    manager = ResearchJobManager(persistence)

    class EmptySearch:
        def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
            return ()

    worker = FakeResearchWorker(persistence, search=EmptySearch())
    outcome = manager.start_job(
        ResearchJobStartRequest(owner_id="user-1", query="How do I create configuration baselines in SCCM?")
    )

    result = worker(outcome.job.job_id)
    status = manager.get_job_status(outcome.job.job_id)

    assert result is None
    assert status is not None
    assert status.job.status is ResearchJobStatus.ERROR
    assert "Search is unavailable" in (status.job.error or "")
    assert status.progress[-1].phase.value == "error"


def test_stub_query_generator_shapes_procedural_query_toward_official_docs() -> None:
    generator = StubQueryGenerator()
    plan = type('Plan', (), {'objective': 'How do I create configuration baselines in SCCM?'})()

    queries = generator(plan, round_number=1)

    assert any('site:learn.microsoft.com' in query for query in queries)
    assert any('Microsoft Learn' in query for query in queries)
    assert any('configuration baselines' in query.lower() for query in queries)


def test_procedural_query_variants_include_authority_seeking_forms() -> None:
    variants = _procedural_query_variants('How do I create configuration baselines in SCCM?')

    assert any('site:learn.microsoft.com' in variant for variant in variants)
    assert any('official documentation' in variant.lower() for variant in variants)
    assert any('Microsoft Learn create configuration baselines in Configuration Manager' in variant for variant in variants)


def test_authority_signal_prefers_microsoft_learn_for_procedural_query() -> None:
    query = "How do I create configuration baselines in SCCM?"
    official = SearchHit(
        url="https://learn.microsoft.com/en-us/intune/configmgr/compliance/deploy-use/create-configuration-baselines",
        title="Create configuration baselines - Configuration Manager | Microsoft Learn",
        snippet="Official Microsoft Learn documentation.",
    )
    blog = SearchHit(
        url="https://www.anoopcnair.com/how-create-sccm-configuration-items-baselines/",
        title="How to Create SCCM Configuration Items Configuration Baselines",
        snippet="Community blog walkthrough.",
    )

    assert _authority_signal_score(query=query, hit=official) > _authority_signal_score(query=query, hit=blog)
    assert _authority_signal_score(query=query, hit=official) >= 10


def test_general_relevance_rejects_weak_blog_root_and_generic_pdf_for_procedural_query() -> None:
    query = "jak działa configuration baseline w sccm po wdrożeniu na kolekcję komputerów"
    weak_blog = SearchHit(
        url="http://piotrsccm.blogspot.com/",
        title="SCCM",
        snippet="Zdalne wywołanie Configuration Baseline. Po utworzeniu i wdrożeniu na testową kolekcję komputerów...",
    )
    weak_pdf = SearchHit(
        url="http://www.e-szbi.pl/files/Przewodnik_zabezpieczen_systemu_Win_8_1.pdf",
        title="przewodnik zabezpieczeo - systemu windows 8 oraz",
        snippet="PDF guide with mixed Windows security content.",
    )
    strong_doc = SearchHit(
        url="https://learn.microsoft.com/en-us/intune/configmgr/compliance/deploy-use/create-configuration-baselines",
        title="Create configuration baselines - Configuration Manager | Microsoft Learn",
        snippet="Configuration baselines contain predefined configuration items and can be deployed to collections for compliance evaluation.",
    )

    assert _is_relevant_hit(query=query, hit=weak_blog) is False
    assert _is_relevant_hit(query=query, hit=weak_pdf) is False
    assert _is_relevant_hit(
        query=query,
        hit=SearchHit(
            url="https://www.reddit.com/r/SCCM/comments/example/baselines/",
            title="Need help with SCCM baselines",
            snippet="Reddit thread with community opinions.",
        ),
    ) is False
    assert _is_relevant_hit(
        query=query,
        hit=SearchHit(
            url="https://stackoverflow.com/questions/39803370/sccm-configuration-baseline-name-table",
            title="SCCM Configuration Baseline Name table - Stack Overflow",
            snippet="Community Q&A about SCCM baseline internals.",
        ),
    ) is False
    assert _is_relevant_hit(
        query=query,
        hit=SearchHit(
            url="https://gist.github.com/Ioan-Popovici/4a5f932f1a7a0c6c7bc69c092f0b9969",
            title="SCCM Configuration Baseline Script",
            snippet="Community gist with a baseline-related script.",
        ),
    ) is False
    assert _is_relevant_hit(query=query, hit=strong_doc) is True


def test_pre_extraction_filter_prefers_official_docs_and_drops_forum_video_snippet() -> None:
    hits = (
        SearchHit(
            url="https://learn.microsoft.com/en-us/intune/configmgr/compliance/deploy-use/create-configuration-baselines",
            title="Create configuration baselines - Configuration Manager | Microsoft Learn",
            snippet="Official procedural documentation.",
        ),
        SearchHit(
            url="https://www.youtube.com/watch?v=oKk2K_omk7c",
            title="Configuring SCCM Configuration Items and Baselines",
            snippet="Video walkthrough of SCCM baseline setup.",
        ),
        SearchHit(
            url="https://www.reddit.com/r/SCCM/comments/jb1z19/can_i_just_say_how_much_i_love_configuration/",
            title="Can I just say how much I love Configuration Items/Baselines?",
            snippet="Forum discussion about SCCM baselines.",
        ),
        SearchHit(
            url="https://gist.github.com/Ioan-Popovici/4a5f932f1a7a0c6c7bc69c092f0b9969",
            title="SCCM Configuration Baseline Script",
            snippet="Community gist with a baseline-related script.",
        ),
    )

    outcome = _filter_hits_for_extraction(
        query='How do I create configuration baselines in SCCM?',
        hits=hits,
    )

    kept_urls = [hit.url for hit in outcome.kept_hits]
    assert any(url.startswith('https://learn.microsoft.com/') for url in kept_urls)
    assert all('youtube.com' not in url for url in kept_urls)
    assert all('reddit.com' not in url for url in kept_urls)
    assert all('gist.github.com' not in url for url in kept_urls)
    assert outcome.authority_policy_applied is True
    assert outcome.dropped_count >= 2


def test_pre_extraction_filter_caps_secondary_when_two_official_docs_exist() -> None:
    hits = (
        SearchHit(
            url="https://learn.microsoft.com/en-us/intune/configmgr/compliance/deploy-use/create-configuration-baselines",
            title="Create configuration baselines - Configuration Manager | Microsoft Learn",
            snippet="Official procedural documentation.",
        ),
        SearchHit(
            url="https://learn.microsoft.com/en-us/intune/configmgr/compliance/deploy-use/deploy-configuration-baselines",
            title="Deploy configuration baselines - Configuration Manager | Microsoft Learn",
            snippet="Official deployment documentation.",
        ),
        SearchHit(
            url="https://www.anoopcnair.com/how-create-sccm-configuration-items-baselines/",
            title="How to Create SCCM Configuration Items Configuration Baselines",
            snippet="Community tutorial.",
        ),
    )

    outcome = _filter_hits_for_extraction(
        query='How do I create configuration baselines in SCCM?',
        hits=hits,
    )

    kept_urls = tuple(hit.url for hit in outcome.kept_hits)
    assert kept_urls == (
        'https://learn.microsoft.com/en-us/intune/configmgr/compliance/deploy-use/create-configuration-baselines',
        'https://learn.microsoft.com/en-us/intune/configmgr/compliance/deploy-use/deploy-configuration-baselines',
    )


def test_pre_extraction_filter_uses_fallback_when_only_secondary_sources_exist() -> None:
    hits = (
        SearchHit(
            url="https://www.velessoftware.com/blog/deploy-a-sccm-configuration-baseline",
            title="Deploy a SCCM Configuration Baseline",
            snippet="Community blog walkthrough with procedural details.",
        ),
        SearchHit(
            url="https://msendpointmgr.com/2017/04/09/configmgr-configuration-baselines-a-beginners-guide/",
            title="ConfigMgr Configuration Baselines - A Beginners Guide",
            snippet="Secondary technical guide for configuration baselines.",
        ),
    )

    outcome = _filter_hits_for_extraction(
        query='How do I create configuration baselines in SCCM?',
        hits=hits,
    )

    assert len(outcome.kept_hits) >= 1
    assert outcome.fallback_used is True
    assert outcome.authority_policy_applied is True


def test_top_findings_prefers_official_docs_over_blog_video_and_forum_for_procedural_query() -> None:
    findings = (
        ExtractedFinding(
            url="https://learn.microsoft.com/en-us/intune/configmgr/compliance/deploy-use/create-configuration-baselines",
            title="Create configuration baselines - Configuration Manager | Microsoft Learn",
            summary="Official procedural documentation for creating and deploying configuration baselines.",
        ),
        ExtractedFinding(
            url="https://www.anoopcnair.com/how-create-sccm-configuration-items-baselines/",
            title="How to Create SCCM Configuration Items Configuration Baselines",
            summary="Community blog walkthrough for SCCM baselines.",
        ),
        ExtractedFinding(
            url="https://www.youtube.com/watch?v=oKk2K_omk7c",
            title="Configuring SCCM Configuration Items and Baselines",
            summary="Video walkthrough of SCCM baseline setup.",
        ),
        ExtractedFinding(
            url="https://www.reddit.com/r/SCCM/comments/jb1z19/can_i_just_say_how_much_i_love_configuration/",
            title="Can I just say how much I love Configuration Items/Baselines?",
            summary="Forum discussion about SCCM baselines.",
        ),
        ExtractedFinding(
            url="https://stackoverflow.com/questions/39803370/sccm-configuration-baseline-name-table",
            title="SCCM Configuration Baseline Name table - Stack Overflow",
            summary="Community Q&A about SCCM baseline internals.",
        ),
        ExtractedFinding(
            url="https://gist.github.com/Ioan-Popovici/4a5f932f1a7a0c6c7bc69c092f0b9969",
            title="SCCM Configuration Baseline Script",
            summary="Community gist with a baseline-related script.",
        ),
    )

    top = _top_findings(
        findings,
        limit=2,
        query="jak działa configuration baseline w sccm po wdrożeniu na kolekcję komputerów",
    )

    assert len(top) == 2
    assert top[0].url.startswith("https://learn.microsoft.com/")
    assert all("youtube.com" not in finding.url for finding in top)
    assert all("reddit.com" not in finding.url for finding in top)
    assert all("stackoverflow.com" not in finding.url for finding in top)
    assert all("gist.github.com" not in finding.url for finding in top)
