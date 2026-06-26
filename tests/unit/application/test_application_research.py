import pytest

from sourcetrace.application import (
    ChainedSearchAdapter,
    ExternalPdfAnalyzerAdapter,
    ExtractedFinding,
    FakeResearchWorker,
    PdfIngestResult,
    ResearchJobManager,
    ResearchJobStartRequest,
    StubExtractor,
    StubQueryGenerator,
    SearchHit,
    SearxNGSearchAdapter,
    StubSynthesizer,
)
from sourcetrace.application.research_runtime import (
    DeterministicPlanningAnalyzer,
    LlmOfficialSubjectPrecisionJudge,
    OfficialHtmlContentEnricher,
    LlmPlanningAnalyzer,
    LlmResearchSynthesizer,
    LlmSearchRelevanceJudge,
    LlmSubjectSheetBuilder,
    SubjectEntity,
    SubjectSheet,
    ResearchSearchError,
    StubQueryGenerator,
    _authority_signal_score,
    _build_fallback_planning_analysis,
    _build_research_report_prompt,
    _classify_query,
    _compile_research_artifact,
    _derive_branch_proposals,
    _derive_problem_analysis,
    _entity_match_score,
    LlmOfficialEvidenceFamilyJudge,
    LlmOfficialEvidenceJudge,
    PackedEvidence,
    _consolidate_official_finding_families,
    _project_source_refs,
    _planning_analysis_to_problem_analysis,
    _planning_aware_query_variants,
    _query_generation_trace,
    _should_promote_official_general_finding_to_core,
    _derive_reflection,
    _enriched_exact_subject_priority_score,
    _exact_subject_content_quality_score,
    _evaluate_branch_proposals,
    _evaluate_research_result,
    _filter_hits_for_extraction,
    _filter_hits_for_extraction_with_diagnostics,
    _is_relevant_hit,
    _lint_compiled_research_artifact,
    _looks_like_listing_page,
    _llm_or_heuristic_relevant_hit,
    _lift_exact_subject_official_findings,
    _pack_evidence_for_synthesis,
    _pdf_ingest_summary,
    _planning_audit_institutional_query_variants,
    _planning_tax_official_query_variants,
    _search_rejection_summary,
    _triage_official_pdf_candidate,
    _source_type,
    _procedural_query_bias,
    _procedural_directness_score,
    _procedural_query_variants,
    _procedural_task_match_score,
    _project_source_refs,
    _research_report_prompt_overlay,
    _top_findings,
    _to_research_evidence_pack,
    build_procedural_admin_unified_search_adapter,
    build_provider_search_adapter,
    build_search_adapter,
)
from sourcetrace.domain import (
    CompiledResearchArtifact,
    CompiledResearchClaim,
    CompiledResearchArtifactLintStatus,
    CompiledResearchEvidenceRef,
    EntityHypothesis,
    PlanningAnalysis,
    PlanningExecutionMode,
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


class FailingProviderSearch:
    provider_name = "searxng"

    def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
        self.last_provider_names = (self.provider_name,)
        raise ResearchSearchError("searxng is unavailable")


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


def test_query_generation_trace_marks_planning_aware_tax_path() -> None:
    planning = PlanningAnalysis(
        query_class=ResearchQueryClass.GENERAL,
        goal="Find official tax rules for private rental in Poland.",
        focus_areas=("official_findings",),
        constraints=("prefer official sources first",),
    )
    plan = ResearchExecutionPlan(
        strategy=ResearchPlanStrategy.DIRECT_ANSWER,
        objective="najem prywatny ryczałt obowiązki podatkowe MF KAS podatki.gov.pl",
    )

    trace = _query_generation_trace(
        plan=plan,
        planning_analysis=planning,
        round_number=1,
    )

    assert trace["path"] == "planning_aware"
    assert trace["prefers_official_sources"] is True
    assert trace["planning_aware_query_count"] >= 1


def test_planning_aware_query_variants_bridge_procedural_public_law_tax_queries() -> None:
    planning = PlanningAnalysis(
        query_class=ResearchQueryClass.PROCEDURAL_ADMIN,
        goal="Find official tax rules and obligations for private rental in Poland.",
        focus_areas=("official_findings",),
        constraints=("prefer official sources first",),
    )

    queries = _planning_aware_query_variants(
        objective="najem prywatny obowiązki podatkowe MF KAS podatki.gov.pl",
        round_number=1,
        planning_analysis=planning,
    )

    assert queries
    assert any("site:podatki.gov.pl" in query for query in queries)
    assert not any("learn.microsoft.com" in query for query in queries)


def test_is_relevant_hit_rescues_official_tax_pages_for_public_law_queries() -> None:
    hit = SearchHit(
        url="https://www.podatki.gov.pl/podatki-osobiste/pit/informacje-podstawowe/co-jest-opodatkowane/dochody-z-najmu",
        title="Serwis o podatkach - Dochody z najmu - Podatki.gov.pl",
        snippet="Oficjalna informacja o dochodach z najmu i zasadach opodatkowania.",
    )

    assert _is_relevant_hit(
        query="Jakie są regulacje podatkowe przy wynajmowaniu mieszkania w Polsce? MF KAS podatki.gov.pl najem prywatny",
        hit=hit,
    ) is True


def test_llm_official_evidence_judge_returns_structured_verdict() -> None:
    class _StubSynth:
        def __call__(self, prompt: str) -> object:
            class _Result:
                text = '{"verdict":"primary","confidence":0.82,"reason":"direct official answer page"}'
            return _Result()

    judge = LlmOfficialEvidenceJudge(_StubSynth())
    verdict, confidence, reason = judge.judge_hit(
        query="najem prywatny obowiązki podatkowe",
        hit=SearchHit(
            url="https://www.podatki.gov.pl/podatki-osobiste/pit/informacje-podstawowe/co-jest-opodatkowane/dochody-z-najmu",
            title="Dochody z najmu - Podatki.gov.pl",
            snippet="Oficjalna informacja o dochodach z najmu.",
        ),
    )

    assert verdict == "primary"
    assert confidence == pytest.approx(0.82)
    assert reason == "direct official answer page"


def test_filter_hits_for_extraction_uses_official_evidence_judge_verdicts() -> None:
    class _StubJudge:
        def judge_hit(self, *, query: str, hit: SearchHit, planning_analysis=None):
            if "dochody-z-najmu" in hit.url:
                return "primary", 0.91, "main official answer page"
            return "reject", 0.77, "not useful enough"

    hits = (
        SearchHit(
            url="https://www.podatki.gov.pl/podatki-osobiste/pit/informacje-podstawowe/co-jest-opodatkowane/dochody-z-najmu",
            title="Dochody z najmu - Podatki.gov.pl",
            snippet="Oficjalna informacja o dochodach z najmu.",
        ),
        SearchHit(
            url="https://www.gov.pl/web/finanse",
            title="Ministerstwo Finansów - Portal Gov.pl",
            snippet="Strona główna ministerstwa.",
        ),
    )

    result = _filter_hits_for_extraction_with_diagnostics(
        query="Jakie są regulacje podatkowe przy wynajmowaniu mieszkania w Polsce? MF KAS podatki.gov.pl najem prywatny",
        hits=hits,
        official_evidence_judge=_StubJudge(),
    )

    diagnostics = result["diagnostics"]
    by_url = {item["url"]: item for item in diagnostics}
    assert by_url[hits[0].url]["llm_official_evidence_verdict"] == "primary"
    assert by_url[hits[0].url]["reason"] == "llm_official_primary"
    assert by_url[hits[1].url]["llm_official_evidence_verdict"] == "reject"
    assert by_url[hits[1].url]["reason"] == "llm_official_reject"
    kept_urls = result["kept_urls"]
    assert hits[0].url in kept_urls
    assert hits[1].url not in kept_urls


def test_pack_evidence_prefers_llm_official_primary_and_drops_collateral() -> None:
    findings = (
        ExtractedFinding(
            url="https://www.podatki.gov.pl/podatki-osobiste/pit/informacje-podstawowe/co-jest-opodatkowane/dochody-z-najmu",
            title="Dochody z najmu - Podatki.gov.pl",
            summary="[llm_official_evidence:primary] llm_official_confidence=0.91; Oficjalna informacja o dochodach z najmu.",
            official_evidence_verdict="primary",
            official_evidence_confidence=0.91,
        ),
        ExtractedFinding(
            url="https://www.gov.pl/web/finanse",
            title="Ministerstwo Finansów - Portal Gov.pl",
            summary="[llm_official_evidence:collateral] llm_official_confidence=0.62; Strona główna ministerstwa.",
            official_evidence_verdict="collateral",
            official_evidence_confidence=0.62,
        ),
        ExtractedFinding(
            url="https://example.com/context",
            title="Context page",
            summary="Some general context.",
        ),
    )

    packed = _pack_evidence_for_synthesis(
        query="Jakie są regulacje podatkowe przy wynajmowaniu mieszkania w Polsce? MF KAS podatki.gov.pl najem prywatny",
        findings=findings,
    )

    assert findings[0] in packed.core
    assert findings[1] in packed.background


def test_pack_evidence_never_places_collateral_official_pages_in_core_for_getback_like_case() -> None:
    findings = (
        ExtractedFinding(
            url="https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html",
            title="Nadzór KNF nad spółką GetBack",
            summary="[llm_official_evidence:primary] Główna strona sprawy.",
            official_evidence_verdict="primary",
        ),
        ExtractedFinding(
            url="https://www.nik.gov.pl/aktualnosci/transkrypcje/transkrypcja-wideo-konferencja-getback-2025.html",
            title="Transkrypcja konferencji GetBack",
            summary="[llm_official_family:collateral] [llm_official_evidence:collateral] Materiał poboczny.",
            official_evidence_verdict="collateral",
        ),
    )

    packed = _pack_evidence_for_synthesis(
        query="Co ustaliła NIK w sprawie nadzoru KNF nad spółką GetBack S.A.? Skup się na źródłach oficjalnych.",
        findings=findings,
    )

    assert findings[0] in packed.core
    assert findings[1] not in packed.core
    assert findings[1] in packed.background


def test_top_findings_biases_canonical_official_primary_over_generic_noise() -> None:
    findings = (
        ExtractedFinding(
            url="https://example.com/noise",
            title="Commercial explainer",
            summary="Very long but generic commercial page about rental tax.",
        ),
        ExtractedFinding(
            url="https://www.podatki.gov.pl/podatki-osobiste/pit/informacje-podstawowe/co-jest-opodatkowane/dochody-z-najmu",
            title="Dochody z najmu - Podatki.gov.pl",
            summary="[llm_official_evidence:primary] llm_official_confidence=0.91; Oficjalna informacja o dochodach z najmu.",
            official_evidence_verdict="primary",
            official_evidence_confidence=0.91,
        ),
    )

    ranked = _top_findings(
        findings,
        limit=2,
        query="Jakie są regulacje podatkowe przy wynajmowaniu mieszkania w Polsce? MF KAS podatki.gov.pl najem prywatny",
    )

    assert ranked[0].url == "https://www.podatki.gov.pl/podatki-osobiste/pit/informacje-podstawowe/co-jest-opodatkowane/dochody-z-najmu"


def test_project_source_refs_prefers_official_primary_sources_first() -> None:
    result = ResearchResultArtifact(
        job_id="job-1",
        owner_id="owner",
        query="Co ustaliła NIK w sprawie nadzoru KNF nad spółką GetBack S.A.? Skup się na źródłach oficjalnych.",
        status=ResearchJobStatus.DONE,
        completion_mode=ResearchCompletionMode.FULL,
        result="report",
        raw_report="report",
        category="general",
        stats=ResearchStats(),
        sources=(
            ResearchSource(url="https://www.prawo.pl/biznes/nik-o-getback-banas-zlozyl-zawiadomienie,533783.html", title="Prawo.pl"),
            ResearchSource(url="https://www.nik.gov.pl/plik/id,17074.pdf", title="Collateral PDF"),
            ResearchSource(url="https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html", title="NIK GetBack"),
            ResearchSource(url="https://www.gov.pl/web/prokuratura-krajowa/zawiadomienie-nik-o-popelnieniu-przestepstwa-w-sprawie-getback-sa", title="Gov.pl GetBack"),
        ),
        raw_findings=(
            ResearchFinding(url="https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html", title="NIK GetBack", summary="[llm_official_evidence:primary] main page"),
            ResearchFinding(url="https://www.gov.pl/web/prokuratura-krajowa/zawiadomienie-nik-o-popelnieniu-przestepstwa-w-sprawie-getback-sa", title="Gov.pl GetBack", summary="official supporting"),
            ResearchFinding(url="https://www.nik.gov.pl/plik/id,17074.pdf", title="Collateral PDF", summary="[llm_official_evidence:collateral] archival pdf"),
            ResearchFinding(url="https://www.prawo.pl/biznes/nik-o-getback-banas-zlozyl-zawiadomienie,533783.html", title="Prawo.pl", summary="media coverage"),
        ),
        evidence_pack=PackedEvidence(
            core=(
                ExtractedFinding(url="https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html", title="NIK GetBack", summary="", official_evidence_verdict="primary"),
                ExtractedFinding(url="https://www.gov.pl/web/prokuratura-krajowa/zawiadomienie-nik-o-popelnieniu-przestepstwa-w-sprawie-getback-sa", title="Gov.pl GetBack", summary=""),
            ),
            supporting=(),
            background=(
                ExtractedFinding(url="https://www.nik.gov.pl/plik/id,17074.pdf", title="Collateral PDF", summary="", official_evidence_verdict="collateral"),
            ),
            has_direct_procedural_evidence=False,
        ),
    )
    projected = _project_source_refs(result, ())
    assert projected[0].url == "https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html"
    assert projected[1].url == "https://www.gov.pl/web/prokuratura-krajowa/zawiadomienie-nik-o-popelnieniu-przestepstwa-w-sprawie-getback-sa"
    assert projected[-1].url == "https://www.nik.gov.pl/plik/id,17074.pdf"


def test_consolidate_official_finding_families_marks_noncanonical_official_pages_as_collateral() -> None:
    class _StubFamilyJudge:
        def judge_family(self, *, query: str, findings: tuple[ExtractedFinding, ...]) -> tuple[str, ...]:
            return (findings[0].url,)

    findings = (
        ExtractedFinding(
            url="https://www.podatki.gov.pl/podatki-osobiste/pit/informacje-podstawowe/co-jest-opodatkowane/dochody-z-najmu",
            title="Dochody z najmu - Podatki.gov.pl",
            summary="Primary official page.",
            official_evidence_verdict="supporting",
        ),
        ExtractedFinding(
            url="https://www.podatki.gov.pl/pytania-i-odpowiedzi/mikrorachunek/czy-zryczaltowany-podatek-dochodowy-z-najmu-nieruchomosci-wplacam-na-mikrorachunek-podatkowy",
            title="Czy zryczałtowany podatek dochodowy z najmu nieruchomości...",
            summary="Collateral official page.",
            official_evidence_verdict="supporting",
        ),
    )

    consolidated, trace = _consolidate_official_finding_families(
        findings,
        query="najem prywatny obowiązki podatkowe MF KAS podatki.gov.pl",
        family_judge=_StubFamilyJudge(),
    )

    assert consolidated[0].official_evidence_verdict == "supporting"
    assert consolidated[1].official_evidence_verdict == "collateral"
    assert trace
    assert trace[0]["canonical_urls"] == [findings[0].url]
    assert trace[0]["collateral_urls"] == [findings[1].url]


def test_planning_tax_official_query_variants_prefers_tax_domains() -> None:
    planning = PlanningAnalysis(
        query_class=ResearchQueryClass.GENERAL,
        goal="Find official tax rules for private rental in Poland.",
        focus_areas=("official_findings",),
        constraints=("prefer official sources first",),
    )

    queries = _planning_tax_official_query_variants(
        objective="najem prywatny ryczałt obowiązki podatkowe",
        primary_entity="najem prywatny",
        planning_analysis=planning,
    )

    assert queries
    assert any("site:podatki.gov.pl" in query for query in queries)
    assert any("site:biznes.gov.pl" in query or "site:gov.pl" in query for query in queries)


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


def test_fake_research_worker_stats_reflect_actual_queries_duration_and_provider_path(monkeypatch) -> None:
    persistence = create_in_memory_research_persistence()
    manager = ResearchJobManager(persistence)

    def unified_search(_: str, *, count: int) -> list[dict[str, object]]:
        del count
        return []

    def provider_search(query: str, *, count: int) -> list[dict[str, object]]:
        del count
        return [
            {
                "url": "https://learn.microsoft.com/en-us/mem/configmgr/compliance/deploy-use/create-configuration-baselines",
                "title": "Create configuration baselines - Configuration Manager | Microsoft Learn",
                "snippet": f"Official guidance for {query}.",
            }
        ]

    search = build_procedural_admin_unified_search_adapter(
        current_search=ChainedSearchAdapter(
            FailingProviderSearch(),
            build_search_adapter(search_web=provider_search),
        ),
        unified_search_web=unified_search,
    )
    worker = FakeResearchWorker(
        persistence,
        search=search,
        stop_rails=type("OneRoundRails", (), {"should_stop": lambda self, **kwargs: True})(),
    )
    outcome = manager.start_job(
        ResearchJobStartRequest(
            owner_id="user-1",
            query="how to create configuration baselines in Configuration Manager",
        )
    )
    monkeypatch.setattr("sourcetrace.application.research_runtime.perf_counter", iter((10.0, 13.8)).__next__)

    result = worker(outcome.job.job_id)

    assert result is not None
    assert result.stats.duration_seconds == 3
    assert result.execution_plan is not None
    assert result.stats.queries == len(StubQueryGenerator()(result.execution_plan, round_number=1))
    assert result.stats.search_providers == (
        "procedural_admin_unified_search",
        "searxng",
        "web_search",
    )


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
        source_context="- Source 1\n  - role: core_candidate\n  - type: official_docs\n  - title: Microsoft Learn\n  - url: https://learn.microsoft.com/example\n  - content: documented policy path",
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


def test_procedural_admin_unified_search_adapter_prefers_unified_hits_when_available() -> None:
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
    assert getattr(unified, 'last_provider_names', ()) == ('procedural_admin_unified_search',)


def test_procedural_admin_unified_search_adapter_keeps_unified_hits_even_when_non_official() -> None:
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
    assert hits[0].url == 'https://www.youtube.com/watch?v=123'
    assert getattr(unified, 'last_provider_names', ()) == ('procedural_admin_unified_search',)


def test_procedural_admin_unified_search_adapter_uses_unified_search_for_general_queries() -> None:
    current = build_search_adapter(search_web=lambda query, count=3: [
        {'url': 'https://nik.gov.pl/aktualnosci/szpital-poludniowy.html', 'title': 'NIK - Szpital Południowy', 'snippet': 'Official audit update'}
    ])
    unified = build_procedural_admin_unified_search_adapter(
        current_search=current,
        unified_search_web=lambda query, count=10: [
            {'url': 'https://example.test/media-story', 'title': 'Media story', 'snippet': 'Secondary report'}
        ],
    )

    hits = unified(("Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?",), round_number=1)

    assert hits
    assert hits[0].url == 'https://example.test/media-story'
    assert getattr(unified, 'last_provider_names', ()) == ('procedural_admin_unified_search',)


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


def test_general_official_depth_signal_does_not_promote_off_topic_official_finding() -> None:
    finding = ExtractedFinding(
        url="https://www.nik.gov.pl/aktualnosci/spojnosc-i-infrastruktura/poludniowa-obwodnica-warszawy-s2.html",
        title="NIK o realizacji i odbiorze budowy fragmentu Południowej Obwodnicy Warszawy",
        summary="[official_pdf_ingest:verified] scope=NIK official control document; findings concern road infrastructure.",
        pdf_triage_notes="pdf_ingest_verified",
    )

    assert _should_promote_official_general_finding_to_core(
        query="Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?",
        finding=finding,
    ) is False



def test_evidence_packing_promotes_on_subject_official_general_finding_to_core() -> None:
    findings = (
        ExtractedFinding(
            url="https://www.nik.gov.pl/kontrole/szpital-poludniowy-w-warszawie.html",
            title="Wyniki kontroli NIK - Szpital Południowy w Warszawie",
            summary="[official_pdf_ingest:verified] scope=NIK official control document; findings confirmed for Szpital Południowy w Warszawie.",
            pdf_triage_notes="pdf_ingest_verified",
        ),
        ExtractedFinding(
            url="https://example.org/media-story",
            title="Medialne omówienie sprawy",
            summary="Wtórne omówienie medialne.",
        ),
    )

    packed = _pack_evidence_for_synthesis(
        query="Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?",
        findings=findings,
    )

    assert len(packed.core) == 1
    assert packed.core[0].url == "https://www.nik.gov.pl/kontrole/szpital-poludniowy-w-warszawie.html"



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


def test_fallback_planning_analysis_derives_readable_ssot_from_current_heuristics() -> None:
    planning = DeterministicPlanningAnalyzer()("deep research architecture")
    problem_analysis = _planning_analysis_to_problem_analysis(planning)

    assert planning.query_class is ResearchQueryClass.BROAD_CONCEPT
    assert planning.complexity is ResearchComplexity.HIGH
    assert planning.execution_mode is PlanningExecutionMode.MULTI_STEP
    assert planning.goal == "deep research architecture"
    assert "system_shape" in planning.focus_areas
    assert planning.analysis_version == "planning_analysis_v1_fallback"
    assert problem_analysis.goal == planning.goal
    assert problem_analysis.query_class is planning.query_class


def test_institutional_audit_query_does_not_classify_as_procedural_admin() -> None:
    planning = _build_fallback_planning_analysis("Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?")

    assert planning.query_class is ResearchQueryClass.GENERAL


def test_stub_query_generator_does_not_emit_microsoft_procedural_queries_for_institutional_audit_query() -> None:
    planning = _build_fallback_planning_analysis("Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?")
    plan = ResearchExecutionPlan(
        strategy=ResearchPlanStrategy.DIRECT_ANSWER,
        objective=planning.goal,
        steps=(
            ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Gather the strongest relevant evidence."),
            ResearchExecutionPlanStep(step_id="step-2", kind="write", objective="Answer directly and surface missing verification.", depends_on=("step-1",)),
        ),
    )

    queries = StubQueryGenerator()(plan, round_number=1, planning_analysis=planning)
    joined = " || ".join(queries).lower()

    assert 'learn.microsoft.com' not in joined
    assert 'microsoft learn' not in joined
    assert 'configuration manager' not in joined


def test_fallback_planning_analysis_surfaces_short_acronym_ambiguity() -> None:
    planning = _build_fallback_planning_analysis("PO/KO escalation path")

    assert planning.execution_mode is PlanningExecutionMode.DISAMBIGUATE
    assert [item.surface_form for item in planning.entity_hypotheses] == ["PO", "KO"]
    assert planning.ambiguity_notes
    assert "PO" in planning.ambiguity_notes[0]


def test_llm_planning_analyzer_accepts_valid_structured_payload() -> None:
    class StubSynthesis:
        def __call__(self, prompt: str):
            from types import SimpleNamespace
            return SimpleNamespace(text='''{
                "query_class": "current_news",
                "complexity": "high",
                "execution_mode": "multi_step",
                "goal": "Zbadaj najnowsze oficjalne ustalenia o problemach z SOR w Szpitalu Południowym.",
                "focus_areas": ["official_findings", "hospital_position", "city_position"],
                "constraints": ["prefer_official_sources_first"],
                "entity_hypotheses": [{"surface_form": "Szpital Południowy", "entity_type": "hospital", "canonical_name": "Szpital Południowy w Warszawie", "candidate_meanings": ["public hospital in Warsaw"], "confidence": "high", "reasoning": "Named institution in query."}],
                "ambiguity_notes": []
            }''')

    planning = LlmPlanningAnalyzer(StubSynthesis())(
        "Jakie są najnowsze informacje o problemach z SOR w Szpitalu Południowym w Warszawie?"
    )

    assert planning.analysis_version == "planning_analysis_v1_llm"
    assert planning.query_class is ResearchQueryClass.CURRENT_NEWS
    assert planning.execution_mode is PlanningExecutionMode.MULTI_STEP
    assert "official_findings" in planning.focus_areas
    assert planning.entity_hypotheses[0].surface_form == "Szpital Południowy"


def test_llm_planning_analyzer_normalizes_free_text_focus_and_constraints() -> None:
    class StubSynthesis:
        def __call__(self, prompt: str):
            from types import SimpleNamespace
            return SimpleNamespace(text='''{
                "query_class": "current_news",
                "complexity": "high",
                "execution_mode": "multi_step",
                "goal": "Sprawdź oficjalne ustalenia i stanowiska.",
                "focus_areas": ["wyniki kontroli", "oficjalne stanowiska", "chronologia komunikatów", "zalecenia pokontrolne"],
                "constraints": ["prefer official/institutional sources first"],
                "entity_hypotheses": [{"surface_form": "NIK", "entity_type": "audit_body", "canonical_name": "Najwyższa Izba Kontroli", "candidate_meanings": ["state audit body"], "confidence": "high", "reasoning": "Named audit institution."}],
                "ambiguity_notes": []
            }''')

    planning = LlmPlanningAnalyzer(StubSynthesis())("Co ustaliła NIK?")

    assert planning.focus_areas == (
        "official_findings",
        "official_position",
        "timeline",
        "recommendations",
    )
    assert planning.constraints == ("prefer_official_sources_first",)


def test_llm_planning_analyzer_overrides_procedural_admin_for_institutional_audit_query() -> None:
    class StubSynthesis:
        def __call__(self, prompt: str):
            from types import SimpleNamespace
            return SimpleNamespace(text='''{
                "query_class": "procedural_admin",
                "complexity": "medium",
                "execution_mode": "multi_step",
                "goal": "Ustalić, co NIK stwierdziła w sprawie Szpitala Południowego w Warszawie.",
                "focus_areas": ["wyniki kontroli", "oficjalne stanowiska"],
                "constraints": ["prefer official/institutional sources first"],
                "entity_hypotheses": [{"surface_form": "NIK", "entity_type": "audit_body", "canonical_name": "Najwyższa Izba Kontroli", "candidate_meanings": ["state audit body"], "confidence": "high", "reasoning": "Named audit institution."}],
                "ambiguity_notes": []
            }''')

    planning = LlmPlanningAnalyzer(StubSynthesis())("Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?")

    assert planning.query_class is ResearchQueryClass.GENERAL


def test_llm_planning_analyzer_falls_back_on_invalid_payload() -> None:
    class StubSynthesis:
        def __call__(self, prompt: str):
            from types import SimpleNamespace
            return SimpleNamespace(text='{"query_class": "not_real"}')

    query = "PO/KO escalation path"
    planning = LlmPlanningAnalyzer(StubSynthesis())(query)

    assert planning.analysis_version == "planning_analysis_v1_fallback"
    assert planning.execution_mode is PlanningExecutionMode.DISAMBIGUATE
    assert [item.surface_form for item in planning.entity_hypotheses] == ["PO", "KO"]


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
    planning_analysis = _build_fallback_planning_analysis("How do I create configuration baselines in SCCM?")
    problem_analysis = ProblemAnalysis(
        query_class=ResearchQueryClass.PROCEDURAL_ADMIN,
        complexity=ResearchComplexity.LOW,
        goal="How do I create configuration baselines in SCCM?",
        focus_areas=("task_path", "required_controls", "validation"),
        constraints=("state_exact_steps_only_when_supported_by_evidence",),
    )
    from sourcetrace.application.research_runtime import StubResearchPlanner
    plan = StubResearchPlanner()(
        problem_analysis.goal,
        problem_analysis=problem_analysis,
        planning_analysis=planning_analysis,
    )

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


def test_general_evidence_pack_promotes_one_research_like_analysis_finding_to_core() -> None:
    findings = (
        ExtractedFinding(
            url="https://example.org/remote-work-mental-health-analysis-2024",
            title="Remote work mental health analysis after 2023",
            summary="Research report with evidence about employee loneliness, stress, and wellbeing outcomes.",
        ),
        ExtractedFinding(
            url="https://example.org/remote-work-overview",
            title="Remote work overview after 2023",
            summary="General overview of remote work trends and employee experience.",
        ),
    )

    packed = _pack_evidence_for_synthesis(
        query="Wpływ pracy zdalnej na zdrowie psychiczne pracowników po 2023 roku",
        findings=findings,
    )

    assert len(packed.core) == 1
    assert packed.core[0].url == "https://example.org/remote-work-mental-health-analysis-2024"
    assert len(packed.supporting) >= 1


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
    assert len(evidence_pack.core) <= 1
    assert len(evidence_pack.supporting) >= 1


def test_stub_query_generator_expands_direct_answer_queries_after_first_round() -> None:
    generator = StubQueryGenerator()
    plan = ResearchExecutionPlan(
        strategy=ResearchPlanStrategy.DIRECT_ANSWER,
        objective="How does retrieval-augmented generation differ from deep research agents?",
        steps=(ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Gather evidence."),),
    )

    first_round = generator(plan, round_number=1)
    second_round = generator(plan, round_number=2)

    assert first_round == ("How does retrieval-augmented generation differ from deep research agents?",)
    assert len(second_round) == 3
    assert any("report study" in query for query in second_round)


def test_stub_query_generator_uses_research_shaped_expansion_for_remote_mental_health_query() -> None:
    generator = StubQueryGenerator()
    plan = ResearchExecutionPlan(
        strategy=ResearchPlanStrategy.DIRECT_ANSWER,
        objective="Wpływ pracy zdalnej na zdrowie psychiczne pracowników po 2023 roku",
        steps=(ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Gather evidence."),),
    )

    second_round = generator(plan, round_number=2)

    assert len(second_round) == 3
    assert any("longitudinal study after 2023" in query for query in second_round)
    assert any("survey report after 2023" in query for query in second_round)
    assert any("remote hybrid work mental health study" in query for query in second_round)


def test_stub_query_generator_uses_planning_analysis_for_current_news_first_round() -> None:
    generator = StubQueryGenerator()
    plan = ResearchExecutionPlan(
        strategy=ResearchPlanStrategy.NEWS_RESEARCH,
        objective="Jakie sa najnowsze informacje o problemach z SOR w Szpitalu Poludniowym w Warszawie?",
        steps=(ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Gather recent attributed developments."),),
    )
    planning_analysis = PlanningAnalysis(
        query_class=ResearchQueryClass.CURRENT_NEWS,
        complexity=ResearchComplexity.HIGH,
        execution_mode=PlanningExecutionMode.MULTI_STEP,
        goal=plan.objective,
        focus_areas=("official_findings", "hospital_position", "city_position", "announcements"),
        constraints=("prefer_official_sources_first",),
        entity_hypotheses=(
            EntityHypothesis(
                surface_form="Szpital Poludniowy",
                entity_type="hospital",
                canonical_name="Szpital Poludniowy w Warszawie",
                confidence="high",
                reasoning="Named public hospital in the query.",
            ),
            EntityHypothesis(
                surface_form="Warszawa",
                entity_type="city",
                canonical_name="Warszawa",
                confidence="medium",
                reasoning="Relevant city owner/governing context for the hospital.",
            ),
        ),
        analysis_version="planning_analysis_v1_llm",
    )

    first_round = generator(plan, round_number=1, planning_analysis=planning_analysis)

    assert first_round[0] == plan.objective
    assert any("official statement" in query for query in first_round)
    assert any("site:gov.pl" in query for query in first_round)
    assert any("hospital statement" in query for query in first_round)
    assert any("komunikat" in query or "komunikaty" in query for query in first_round)
    assert len(first_round) <= 8


def test_stub_query_generator_uses_planning_analysis_for_current_news_follow_up_round() -> None:
    generator = StubQueryGenerator()
    plan = ResearchExecutionPlan(
        strategy=ResearchPlanStrategy.NEWS_RESEARCH,
        objective="Jakie sa najnowsze informacje o problemach z SOR w Szpitalu Poludniowym w Warszawie?",
        steps=(ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Gather recent attributed developments."),),
    )
    planning_analysis = PlanningAnalysis(
        query_class=ResearchQueryClass.CURRENT_NEWS,
        complexity=ResearchComplexity.HIGH,
        execution_mode=PlanningExecutionMode.MULTI_STEP,
        goal=plan.objective,
        focus_areas=("official_findings", "hospital_position", "city_position", "timeline"),
        constraints=("prefer_official_sources_first",),
        entity_hypotheses=(
            EntityHypothesis(
                surface_form="Szpital Poludniowy",
                entity_type="hospital",
                canonical_name="Szpital Poludniowy w Warszawie",
                confidence="high",
                reasoning="Named public hospital in the query.",
            ),
        ),
        analysis_version="planning_analysis_v1_llm",
    )

    second_round = generator(plan, round_number=2, planning_analysis=planning_analysis)

    assert any("official statement" in query or "official update" in query for query in second_round)
    assert any("hospital statement" in query for query in second_round)
    assert any("komunikat" in query or "stanowisko" in query for query in second_round)
    assert len(second_round) <= 6


def test_stub_query_generator_uses_entity_aware_official_variants_for_general_institutional_query() -> None:
    generator = StubQueryGenerator()
    plan = ResearchExecutionPlan(
        strategy=ResearchPlanStrategy.DIRECT_ANSWER,
        objective="Co ustalila NIK w sprawie Szpitala Poludniowego w Warszawie?",
        steps=(ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Gather official institutional findings."),),
    )
    planning_analysis = PlanningAnalysis(
        query_class=ResearchQueryClass.GENERAL,
        complexity=ResearchComplexity.HIGH,
        execution_mode=PlanningExecutionMode.MULTI_STEP,
        goal=plan.objective,
        focus_areas=("recommendations", "timeline", "official_findings"),
        constraints=("prefer_official_sources_first",),
        entity_hypotheses=(
            EntityHypothesis(
                surface_form="NIK",
                entity_type="audit_body",
                canonical_name="Najwyzsza Izba Kontroli",
                confidence="high",
                reasoning="The query explicitly asks about NIK findings.",
            ),
        ),
        analysis_version="planning_analysis_v1_llm",
    )

    first_round = generator(plan, round_number=1, planning_analysis=planning_analysis)
    joined = " || ".join(first_round).lower()

    assert "site:nik.gov.pl" in joined or "site:gov.pl" in joined
    assert "informacja o wynikach kontroli" in joined or "raport" in joined or "wyniki kontroli" in joined
    assert "najwyzsza izba kontroli" in joined or "szpital poludniowy" in joined
    assert first_round[0] == plan.objective
    assert len(first_round) <= 8


def test_stub_query_generator_uses_institutional_follow_up_variants_for_general_official_query() -> None:
    generator = StubQueryGenerator()
    plan = ResearchExecutionPlan(
        strategy=ResearchPlanStrategy.DIRECT_ANSWER,
        objective="Co ustalila NIK w sprawie Szpitala Poludniowego w Warszawie?",
        steps=(ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Gather official institutional findings."),),
    )
    planning_analysis = PlanningAnalysis(
        query_class=ResearchQueryClass.GENERAL,
        complexity=ResearchComplexity.MEDIUM,
        execution_mode=PlanningExecutionMode.MULTI_STEP,
        goal="Ustalić, co NIK stwierdziła w sprawie Szpitala Południowego w Warszawie, najlepiej na podstawie oficjalnych materiałów pokontrolnych i komunikatów.",
        focus_areas=("official_findings", "timeline", "recommendations"),
        constraints=("prefer_official_sources_first",),
        entity_hypotheses=(
            EntityHypothesis(
                surface_form="NIK",
                entity_type="audit_body",
                canonical_name="Najwyzsza Izba Kontroli",
                confidence="high",
                reasoning="Named audit institution.",
            ),
            EntityHypothesis(
                surface_form="Szpital Poludniowy",
                entity_type="hospital",
                canonical_name="Szpital Poludniowy w Warszawie",
                confidence="high",
                reasoning="Named hospital.",
            ),
            EntityHypothesis(
                surface_form="Warszawa",
                entity_type="city",
                canonical_name="Warszawa",
                confidence="medium",
                reasoning="Named city.",
            ),
        ),
        analysis_version="planning_analysis_v1_llm",
    )

    second_round = generator(plan, round_number=2, planning_analysis=planning_analysis)

    joined = " || ".join(second_round).lower()
    assert "site:nik.gov.pl" in joined or "site:gov.pl" in joined
    assert "informacja o wynikach kontroli" in joined or "raport" in joined or "wyniki kontroli" in joined
    assert "najwyzsza izba kontroli" in joined or "szpital poludniowy w warszawie" in joined
    assert "report study" not in joined
    assert "analysis findings" not in joined
    assert "workplace health research" not in joined


def test_stub_query_generator_uses_institutional_follow_up_variants_for_real_live_nik_payload_shape() -> None:
    generator = StubQueryGenerator()
    plan = ResearchExecutionPlan(
        strategy=ResearchPlanStrategy.DIRECT_ANSWER,
        objective="Ustalić, co NIK stwierdziła w sprawie Szpitala Południowego w Warszawie, najlepiej na podstawie oficjalnych materiałów pokontrolnych i komunikatów.",
        steps=(ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Gather official institutional findings."),),
    )
    planning_analysis = PlanningAnalysis(
        query_class=ResearchQueryClass.GENERAL,
        complexity=ResearchComplexity.MEDIUM,
        execution_mode=PlanningExecutionMode.MULTI_STEP,
        goal=plan.objective,
        focus_areas=(
            "ustalenia_nik_i_główne_zarzuty/wnioski",
            "oficjalny_raport,_informacja_o_wynikach_kontroli,_komunikaty_prasowe",
            "zakres_sprawy:_szpital_południowy_w_warszawie",
        ),
        constraints=(
            "preferuj_oficjalne_źródła_nik_i_dokumenty_urzędowe",
            "uwzględnij_możliwość,_że_sprawa_dotyczy_konkretnej_kontroli_lub_okresu",
            "krótko_odróżnij_ustalenia_od_komentarzy_medialnych",
        ),
        entity_hypotheses=(
            EntityHypothesis(
                surface_form="NIK",
                entity_type="institution",
                canonical_name="Najwyższa Izba Kontroli",
                confidence="0.99",
                reasoning="W polskim kontekście publicznym skrót NIK niemal zawsze oznacza organ kontroli państwowej.",
            ),
            EntityHypothesis(
                surface_form="Szpital Południowy w Warszawie",
                entity_type="institution",
                canonical_name="Szpital Południowy w Warszawie",
                confidence="0.9",
                reasoning="To konkretna warszawska placówka publiczna.",
            ),
            EntityHypothesis(
                surface_form="w sprawie",
                entity_type="event",
                canonical_name="kontrola lub postępowanie dotyczące Szpitala Południowego",
                confidence="0.76",
                reasoning="Pytanie sugeruje ustalenia organu kontrolnego.",
            ),
        ),
        analysis_version="planning_analysis_v1_llm",
    )

    second_round = generator(plan, round_number=2, planning_analysis=planning_analysis)
    joined = " || ".join(second_round).lower()

    assert "site:nik.gov.pl" in joined or "site:gov.pl" in joined or "site:podatki.gov.pl" in joined
    assert "najwyższa izba kontroli" in joined or "najwyzsza izba kontroli" in joined
    assert "ministerstwo finansów" in joined or "ministerstwo finansow" in joined or "kas" in joined or "szpital południowy" in joined or "szpital poludniowy" in joined
    assert "report study" not in joined
    assert "analysis findings" not in joined
    assert "workplace health research" not in joined


def test_stub_query_generator_uses_polish_official_shaping_from_normalized_focus() -> None:
    generator = StubQueryGenerator()
    plan = ResearchExecutionPlan(
        strategy=ResearchPlanStrategy.NEWS_RESEARCH,
        objective="Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?",
        steps=(ResearchExecutionPlanStep(step_id="step-1", kind="search", objective="Gather official institutional findings."),),
    )
    planning_analysis = PlanningAnalysis(
        query_class=ResearchQueryClass.CURRENT_NEWS,
        complexity=ResearchComplexity.HIGH,
        execution_mode=PlanningExecutionMode.MULTI_STEP,
        goal=plan.objective,
        focus_areas=("wyniki kontroli", "oficjalne stanowiska", "chronologia komunikatów", "zalecenia pokontrolne"),
        constraints=("prefer official/institutional sources first",),
        entity_hypotheses=(
            EntityHypothesis(
                surface_form="NIK",
                entity_type="audit_body",
                canonical_name="Najwyższa Izba Kontroli",
                confidence="high",
                reasoning="Named audit body.",
            ),
        ),
        analysis_version="planning_analysis_v1_llm",
    )

    first_round = generator(plan, round_number=1, planning_analysis=planning_analysis)

    assert any("Najwyższa Izba Kontroli informacja o wynikach kontroli" in query for query in first_round)
    assert any("Najwyższa Izba Kontroli official statement" in query for query in first_round)
    assert any("site:nik.gov.pl" in query for query in first_round)
    assert len(first_round) <= 8


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


def test_build_provider_search_adapter_prefers_unified_search_before_searxng() -> None:
    def search_web(query: str, *, count: int) -> list[dict[str, object]]:
        return [{"url": "https://unified.example/result", "title": query, "snippet": "unified"}]

    adapter = build_provider_search_adapter(
        search_web=search_web,
        searxng_base_url="http://example.test",
    )

    assert isinstance(adapter, ChainedSearchAdapter)
    assert [getattr(item, 'provider_name', '?') for item in adapter.adapters] == ['web_search', 'searxng']


def test_procedural_admin_unified_search_adapter_uses_unified_first_for_institutional_general_query() -> None:
    searx_calls: list[tuple[str, ...]] = []

    class CurrentSearch:
        provider_name = 'searxng'
        active_provider_names = ('searxng',)

        def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
            searx_calls.append(queries)
            return (SearchHit(url='https://fallback.example', title='Fallback', snippet='Fallback'),)

    def unified_search_web(query: str, count: int = 10) -> list[dict[str, object]]:
        return [
            {
                'url': 'https://www.nik.gov.pl/aktualnosci/dzialania-nik-w-obszarze-ochrony-zdrowia.html',
                'title': 'Działania NIK w obszarze ochrony zdrowia',
                'snippet': 'Zapowiedź publikacji wyników kontroli dotyczącej Warszawskiego Szpitala Południowego.',
            }
        ]

    adapter = build_procedural_admin_unified_search_adapter(
        current_search=CurrentSearch(),
        unified_search_web=unified_search_web,
    )

    hits = adapter(("Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?",), round_number=1)

    assert hits
    assert hits[0].url == 'https://www.nik.gov.pl/aktualnosci/dzialania-nik-w-obszarze-ochrony-zdrowia.html'
    assert searx_calls == []


def test_triage_official_pdf_candidate_marks_subject_phrase_matching_pdf_as_relevant() -> None:
    hit = SearchHit(
        url='https://www.nik.gov.pl/kontrole/wyniki-kontroli-nik/pobierz,control-note.pdf',
        title='Wystąpienie pokontrolne Delegatury NIK',
        snippet='Dokument dotyczy Szpitala Południowego w Warszawie i zawiera ustalenia kontroli.',
    )

    verdict, notes = _triage_official_pdf_candidate(
        query='Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?',
        hit=hit,
    )

    assert verdict == 'relevant'
    assert notes in {'subject_phrase_match', 'subject_anchor_match'}


def test_triage_official_pdf_candidate_marks_subject_matching_pdf_as_relevant() -> None:
    hit = SearchHit(
        url='https://www.nik.gov.pl/kontrole/wyniki-kontroli-nik/pobierz,lwa~d_21_505_202301131327521673612872~id0~01,typ,kj.pdf',
        title='Wystąpienie pokontrolne',
        snippet='Dokument zawiera odniesienia do Szpitala Południowego w Warszawie oraz ustaleń kontroli.',
    )

    verdict, notes = _triage_official_pdf_candidate(
        query='Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?',
        hit=hit,
    )

    assert verdict == 'relevant'
    assert notes == 'subject_anchor_match'


def test_stub_extractor_adds_pdf_triage_prefix_for_official_pdf() -> None:
    extractor = StubExtractor(query='Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?')
    findings = extractor((
        SearchHit(
            url='https://www.nik.gov.pl/kontrole/wyniki-kontroli-nik/pobierz,lwa~d_21_505_202301131327521673612872~id0~01,typ,kj.pdf',
            title='Wystąpienie pokontrolne',
            snippet='Szpital Południowy w Warszawie i ustalenia kontroli.',
        ),
    ))

    assert len(findings) == 1
    assert findings[0].pdf_triage_verdict in {'relevant', 'uncertain', 'irrelevant'}
    assert findings[0].pdf_triage_notes in {'subject_anchor_match', 'subject_phrase_match', 'partial_subject_match', 'entity_match_without_anchor', 'no_subject_signal'}
    assert findings[0].summary.startswith(f'[official_pdf_triage:{findings[0].pdf_triage_verdict}]')


def test_pdf_ingest_result_can_be_rendered_into_verified_summary() -> None:
    result = PdfIngestResult(
        relevant=True,
        confidence=0.91,
        document_scope='NIK official control document',
        entity_match_summary='Szpital Południowy w Warszawie',
        key_findings=('Potwierdzono nieprawidłowości',),
        evidence_pages=(3, 4),
    )

    summary = _pdf_ingest_summary(result)

    assert 'scope=NIK official control document' in summary
    assert 'entity=Szpital Południowy w Warszawie' in summary
    assert 'pages=3,4' in summary
    assert 'Potwierdzono nieprawidłowości' in summary


def test_external_pdf_analyzer_adapter_delegates_to_analyzer() -> None:
    seen: dict[str, object] = {}

    def analyzer(**kwargs):
        seen.update(kwargs)
        return PdfIngestResult(
            relevant=True,
            confidence=0.88,
            document_scope='external analyzer result',
            entity_match_summary='Szpital Południowy',
            key_findings=('Zewnętrzny analyzer działa',),
            evidence_pages=(2,),
        )

    adapter = ExternalPdfAnalyzerAdapter(analyzer)
    result = adapter(
        query='Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?',
        url='https://example.test/report.pdf',
        title='Raport PDF',
        triage_verdict='relevant',
    )

    assert seen['url'] == 'https://example.test/report.pdf'
    assert result.relevant is True
    assert result.document_scope == 'external analyzer result'


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


def test_general_filter_promotes_research_like_analysis_hit_into_strong_bucket() -> None:
    promoted = SearchHit(
        url="https://example.org/research/remote-work-mental-health-analysis-2024",
        title="Longitudinal analysis of remote work and employee mental health after 2023",
        snippet="Detailed analysis with post-2023 findings on remote work, employee loneliness, stress, wellbeing outcomes, and mental health risks in hybrid versus remote settings.",
    )
    secondary = SearchHit(
        url="https://example.org/remote-work-overview",
        title="Remote work overview after 2023",
        snippet="General overview of remote work trends and employee experience.",
    )

    outcome = _filter_hits_for_extraction(
        query="Wpływ pracy zdalnej na zdrowie psychiczne pracowników po 2023 roku",
        hits=(promoted, secondary),
    )

    assert outcome.authority_policy_applied is True
    assert outcome.fallback_used is False
    assert len(outcome.kept_hits) >= 1
    assert outcome.kept_hits[0].url == promoted.url


def test_source_type_recognizes_research_domain_blog_as_analysis() -> None:
    assert _source_type(
        "https://research.ibm.com/blog/retrieval-augmented-generation-RAG",
        "What is retrieval-augmented generation (RAG)? - IBM Research",
    ) == "analysis"


def test_source_type_recognizes_longitudinal_title_as_analysis() -> None:
    assert _source_type(
        "https://example.org/workplace-longitudinal-study",
        "Longitudinal study of remote work and employee wellbeing",
    ) == "analysis"


def test_source_type_recognizes_gov_and_pubmed_as_official_docs() -> None:
    assert _source_type(
        "https://www.nik.gov.pl/aktualnosci/szpital-poludniowy.html",
        "Wyniki kontroli NIK",
    ) == "official_docs"
    assert _source_type(
        "https://pubmed.ncbi.nlm.nih.gov/12345678/",
        "Remote work and mental health after 2023",
    ) == "official_docs"


def test_filter_hits_preserves_official_candidate_for_institutional_query() -> None:
    official = SearchHit(
        url="https://www.nik.gov.pl/aktualnosci/szpital-poludniowy.html",
        title="Wyniki kontroli NIK",
        snippet="Oficjalny komunikat o wynikach kontroli.",
    )
    generic = SearchHit(
        url="https://example.org/news-wrap",
        title="Remote work and mental health trends",
        snippet="General article.",
    )

    outcome = _filter_hits_for_extraction(
        query="Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?",
        hits=(generic, official),
    )

    urls = [hit.url for hit in outcome.kept_hits]
    assert official.url in urls
    assert outcome.authority_policy_applied is True


def test_filter_hits_preserves_scientific_candidate_for_scientific_query() -> None:
    scientific = SearchHit(
        url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
        title="Systematic review of remote work and mental health after 2023",
        snippet="Peer-reviewed synthesis.",
    )
    generic = SearchHit(
        url="https://example.org/news-wrap",
        title="Remote work and mental health trends",
        snippet="General article.",
    )

    outcome = _filter_hits_for_extraction(
        query="Wpływ pracy zdalnej na zdrowie psychiczne pracowników po 2023 roku",
        hits=(generic, scientific),
    )

    urls = [hit.url for hit in outcome.kept_hits]
    assert scientific.url in urls
    assert outcome.authority_policy_applied is True


def test_institutional_weighting_orders_official_before_generic_media() -> None:
    official = SearchHit(
        url="https://www.nik.gov.pl/aktualnosci/szpital-poludniowy.html",
        title="Wyniki kontroli NIK",
        snippet="Oficjalny komunikat o wynikach kontroli.",
    )
    media = SearchHit(
        url="https://example.org/media-story",
        title="Głośna sprawa szpitala południowego",
        snippet="Wtórne omówienie medialne.",
    )

    outcome = _filter_hits_for_extraction(
        query="Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?",
        hits=(media, official),
    )

    assert outcome.kept_hits[0].url == official.url


def test_institutional_entity_match_prefers_exact_official_subject_over_broad_official_page() -> None:
    exact = SearchHit(
        url="https://www.nik.gov.pl/kontrole/szpital-poludniowy-w-warszawie.html",
        title="Wyniki kontroli NIK - Szpital Południowy w Warszawie",
        snippet="Oficjalna informacja o wynikach kontroli dotyczącej Szpitala Południowego w Warszawie.",
    )
    broad = SearchHit(
        url="https://www.nik.gov.pl/aktualnosci/dzialania-nik-w-obszarze-ochrony-zdrowia.html",
        title="Działania NIK w obszarze ochrony zdrowia",
        snippet="Zbiorcza strona o działaniach NIK w sektorze zdrowia.",
    )

    outcome = _filter_hits_for_extraction(
        query="Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?",
        hits=(broad, exact),
    )

    assert outcome.kept_hits[0].url == exact.url


def test_institutional_entity_match_prefers_exact_school_subject_over_broad_ministry_page() -> None:
    exact = SearchHit(
        url="https://www.gov.pl/web/edukacja/zespol-szkol-nr-2-w-radomiu-wyniki-kontroli",
        title="Wyniki kontroli - Zespół Szkół nr 2 w Radomiu",
        snippet="Oficjalna informacja dotycząca konkretnej szkoły i wyników kontroli.",
    )
    broad = SearchHit(
        url="https://www.gov.pl/web/edukacja/kontrole-w-oswiacie",
        title="Kontrole w oświacie - Ministerstwo Edukacji",
        snippet="Przegląd działań kontrolnych w sektorze edukacji.",
    )

    outcome = _filter_hits_for_extraction(
        query="Co wykazała kontrola ministerstwa w Zespole Szkół nr 2 w Radomiu?",
        hits=(broad, exact),
    )

    assert outcome.kept_hits[0].url == exact.url


def test_institutional_off_topic_official_hit_is_dropped_before_extraction() -> None:
    exact = SearchHit(
        url="https://www.nik.gov.pl/kontrole/szpital-poludniowy-w-warszawie.html",
        title="Wyniki kontroli NIK - Szpital Południowy w Warszawie",
        snippet="Oficjalna informacja o wynikach kontroli dotyczącej Szpitala Południowego w Warszawie.",
    )
    broad = SearchHit(
        url="https://www.nik.gov.pl/aktualnosci/dzialania-nik-w-obszarze-ochrony-zdrowia.html",
        title="Działania NIK w obszarze ochrony zdrowia",
        snippet="Zbiorcza strona o działaniach NIK w sektorze zdrowia.",
    )

    outcome = _filter_hits_for_extraction(
        query="Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?",
        hits=(broad, exact),
    )

    urls = [hit.url for hit in outcome.kept_hits]
    assert exact.url in urls
    assert broad.url not in urls


def test_institutional_short_official_slug_is_not_dropped_as_off_topic() -> None:
    official = SearchHit(
        url="https://www.nik.gov.pl/aktualnosci/szpital-poludniowy.html",
        title="Wyniki kontroli NIK",
        snippet="Oficjalny komunikat o wynikach kontroli.",
    )

    outcome = _filter_hits_for_extraction(
        query="Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?",
        hits=(official,),
    )

    assert [hit.url for hit in outcome.kept_hits] == [official.url]


def test_institutional_relevant_hit_admits_short_official_subject_slug() -> None:
    official = SearchHit(
        url="https://www.nik.gov.pl/aktualnosci/szpital-poludniowy.html",
        title="Wyniki kontroli NIK",
        snippet="Oficjalny komunikat o wynikach kontroli.",
    )

    assert _is_relevant_hit(
        query="Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?",
        hit=official,
    ) is True


def test_institutional_relevant_hit_rejects_official_surface_overlap_without_subject_anchor() -> None:
    official = SearchHit(
        url="https://www.nik.gov.pl/aktualnosci/spojnosc-i-infrastruktura/poludniowa-obwodnica-warszawy-s2.html",
        title="NIK o realizacji i odbiorze budowy fragmentu Południowej Obwodnicy Warszawy",
        snippet="Kontrola dotyczy inwestycji drogowej.",
    )

    assert _is_relevant_hit(
        query="Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?",
        hit=official,
    ) is False


def test_planning_audit_query_variants_include_subject_specific_nik_artifact_queries() -> None:
    planning = PlanningAnalysis(
        query_class=ResearchQueryClass.GENERAL,
        goal="Ustalić, co NIK stwierdziła w sprawie Szpitala Południowego w Warszawie.",
        focus_areas=("official_findings",),
        constraints=("preferować_oficjalne_źródła_publiczne_w_pierwszej_kolejności",),
        entity_hypotheses=(
            EntityHypothesis(surface_form="NIK", canonical_name="Najwyższa Izba Kontroli", entity_type="institution"),
            EntityHypothesis(surface_form="Szpital Południowy", canonical_name="Szpital Południowy w Warszawie", entity_type="hospital"),
        ),
    )

    queries = _planning_audit_institutional_query_variants(
        objective="Co ustaliła NIK w sprawie Szpitala Południowego w Warszawie?",
        round_number=1,
        primary_entity="Najwyższa Izba Kontroli",
        planning_analysis=planning,
    )

    assert any('site:nik.gov.pl "Szpital Południowy w Warszawie" "informacja o wynikach kontroli"' == item for item in queries)
    assert any('site:nik.gov.pl "Szpital Południowy w Warszawie" pdf' == item for item in queries)


def test_scientific_weighting_orders_analysis_before_generic_media() -> None:
    analysis = SearchHit(
        url="https://example.org/research/remote-work-mental-health-analysis-2024",
        title="Longitudinal analysis of remote work and employee mental health after 2023",
        snippet="Peer-reviewed style synthesis.",
    )
    media = SearchHit(
        url="https://example.org/media-story",
        title="Remote work trends after 2023",
        snippet="General article.",
    )

    outcome = _filter_hits_for_extraction(
        query="Wpływ pracy zdalnej na zdrowie psychiczne pracowników po 2023 roku",
        hits=(media, analysis),
    )

    assert outcome.kept_hits[0].url == analysis.url


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


def test_institutional_relevant_hit_rescues_nik_official_pdf_with_query_local_overlap() -> None:
    hit = SearchHit(
        title="[PDF] Funkcjonowanie systemu ratownictwa medycznego - Najwyższa Izba Kontroli",
        snippet="Dokument pokontrolny NIK o funkcjonowaniu systemu ratownictwa medycznego.",
        url="https://www.nik.gov.pl/kontrole/wyniki-kontroli-nik/pobierz,lby~p_19_105_201912100929151575966555~id1~01,typ,kj.pdf",
    )

    assert _is_relevant_hit(
        query="Jakie były główne ustalenia NIK w sprawie funkcjonowania systemu ratownictwa medycznego?",
        hit=hit,
    ) is True


def test_institutional_relevant_hit_rejects_official_pdf_without_query_local_overlap() -> None:
    hit = SearchHit(
        title="[PDF] SPRAWOZDANIE - Najwyższa Izba Kontroli",
        snippet="Ogólne efekty działalności NIK w 2024 roku.",
        url="https://www.nik.gov.pl/plik/id,31066,vp,34379.pdf",
    )

    assert _is_relevant_hit(
        query="Jakie były główne ustalenia NIK w sprawie funkcjonowania systemu ratownictwa medycznego?",
        hit=hit,
    ) is False

def test_llm_search_relevance_judge_can_rescue_official_hit_with_subject_match_summary() -> None:
    judge = LlmSearchRelevanceJudge(lambda prompt: type('R', (), {'text': '{"relevant": true, "confidence": 0.93, "reason": "Official subject match"}'})())
    hit = SearchHit(
        url='https://um.warszawa.pl/-/informacja-m-st-warszawy-o-dalszych-dzialaniach-podjetych-w-sprawie-warszawskiego-szpitala-poludniowego',
        title='Informacja m.st. Warszawy o dalszych działaniach podjętych w sprawie Warszawskiego Szpitala Południowego',
        snippet='Oficjalny komunikat miasta o dalszych działaniach wokół szpitala.',
    )

    assert _llm_or_heuristic_relevant_hit(
        query='jakie są oficjalnie potwierdzone ustalenia i decyzje wokół kontroli SOR Szpitala Południowego w Warszawie',
        hit=hit,
        relevance_judge=judge,
    ) is True

def test_filter_hits_for_extraction_allows_llm_rescue_for_official_adjacent_hit() -> None:
    hit = SearchHit(
        url='https://www.gov.pl/web/po-warszawa/dwa-sledztwa-prokuratury-okregowej-w-warszawie-w-zakresie-stwierdzonych-nieprawidlowosci-w-funkcjonowaniu-sor-warszawskiego-szpitala-poludniowego',
        title='Dwa śledztwa Prokuratury Okręgowej w Warszawie w zakresie stwierdzonych nieprawidłowości w funkcjonowaniu SOR Warszawskiego Szpitala Południowego',
        snippet='Oficjalny komunikat prokuratury dotyczący nieprawidłowości i dalszych działań.',
    )
    judge = LlmSearchRelevanceJudge(lambda prompt: type('R', (), {'text': '{"relevant": true, "confidence": 0.91, "reason": "On-subject official hit"}'})())

    analysis = _filter_hits_for_extraction_with_diagnostics(
        query='jakie są oficjalnie potwierdzone ustalenia i decyzje wokół kontroli SOR Szpitala Południowego w Warszawie',
        hits=(hit,),
        relevance_judge=judge,
    )

    assert analysis['outcome'].kept_count == 1
    assert analysis['outcome'].kept_hits[0].url == hit.url

def test_llm_subject_sheet_builder_prefers_structured_llm_payload() -> None:
    builder = LlmSubjectSheetBuilder(lambda prompt: type('R', (), {'text': '{"query_summary":"Kontrola SOR","primary_subject":{"name":"Szpitalny Oddział Ratunkowy Szpitala Południowego w Warszawie","type":"hospital_emergency_department","confidence":0.95},"related_entities":[{"name":"Szpital Południowy w Warszawie","type":"hospital","role":"parent","confidence":0.92}],"aliases":["SOR Szpitala Południowego"],"anchor_terms":["szpital poludniowy","sor szpital poludniowy"],"proceeding_terms":["kontrola","ustalenia"],"must_have_signals":["subject match"],"acceptable_adjacent_signals":["stanowisko miasta"],"disqualifying_signals":["inny szpital"],"official_source_hints":[{"kind":"domain","value":"gov.pl"}]}'})())
    sheet = builder(query='kontrola SOR Szpitala Południowego')

    assert sheet.primary_subject.name == 'Szpitalny Oddział Ratunkowy Szpitala Południowego w Warszawie'
    assert 'SOR Szpitala Południowego' in sheet.aliases
    assert any(item.value == 'gov.pl' for item in sheet.official_source_hints)


def test_entity_match_score_uses_subject_sheet_aliases() -> None:
    sheet = SubjectSheet(
        query_summary='Kontrola SOR',
        primary_subject=SubjectEntity(name='Szpitalny Oddział Ratunkowy Szpitala Południowego w Warszawie', type='hospital_emergency_department', confidence=0.9),
        aliases=('SOR Szpitala Południowego', 'Szpital Południowy w Warszawie'),
        anchor_terms=('szpital poludniowy', 'sor szpital poludniowy'),
    )
    hit = SearchHit(
        url='https://www.gov.pl/web/rpp/oswiadczenie-rzecznika-praw-pacjenta-w-sprawie-nieprawidlowosci-w-szpitalu-poludniowym',
        title='Oświadczenie Rzecznika Praw Pacjenta w sprawie nieprawidłowości w Szpitalu Południowym',
        snippet='Oficjalny komunikat dotyczący nieprawidłowości w SOR Szpitala Południowego.',
    )

    assert _entity_match_score(query='kontrola SOR Szpitala Południowego', hit=hit, subject_sheet=sheet) >= 5



def test_llm_official_subject_precision_judge_distinguishes_exact_subject() -> None:
    judge = LlmOfficialSubjectPrecisionJudge(lambda prompt: type('R', (), {'text': '{"subject_match":"exact_subject","confidence":0.93,"reason":"Directly names GetBack and KNF oversight case."}'})())
    match, confidence, reason = judge.judge_hit(
        query='Co ustaliła NIK w sprawie nadzoru KNF nad spółką GetBack S.A.?',
        hit=SearchHit(
            url='https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html',
            title='Nierzetelny i nieprawidłowy nadzór KNF nad spółką GetBack S.A.',
            snippet='Oficjalny komunikat NIK o ustaleniach dotyczących GetBack.',
        ),
    )

    assert match == 'exact_subject'
    assert confidence == 0.93
    assert 'GetBack' in reason



def test_pack_evidence_prefers_exact_subject_tagged_official_finding() -> None:
    findings = (
        ExtractedFinding(
            url='https://www.nik.gov.pl/plik/id,6423,vp,8193.pdf',
            title='FUNKCJONOWANIE SYSTEMU OCHRONY PRAW KLIENTÓW ...',
            summary='[official_subject:related_but_broad] confidence=0.70; reason=Broad market context — official broad KNF context.',
        ),
        ExtractedFinding(
            url='https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html',
            title='Nierzetelny i nieprawidłowy nadzór KNF nad spółką GetBack S.A.',
            summary='[official_subject:exact_subject] confidence=0.95; reason=Directly about GetBack — official NIK case page.',
        ),
    )

    packed = _pack_evidence_for_synthesis(
        query='Co ustaliła NIK w sprawie nadzoru KNF nad spółką GetBack S.A.?',
        findings=findings,
    )

    assert packed.core
    assert packed.core[0].url == 'https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html'



def test_lift_exact_subject_official_finding_marks_primary_case_page() -> None:
    finding = ExtractedFinding(
        url='https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html',
        title='Nierzetelny i nieprawidłowy nadzór KNF nad spółką GetBack S.A.',
        summary='[official_subject:exact_subject] Jul 8, 2025 ... Wartość wierzytelności objętych układem wyniosła blisko 3,14 mld zł. Key evidence: 8; 2025; 3,14.',
    )

    lifted = _lift_exact_subject_official_findings(
        query='Co ustaliła NIK w sprawie nadzoru KNF nad spółką GetBack S.A.?',
        findings=(finding,),
    )

    assert '[exact_subject_content_lift:prefer_primary_case_page]' in lifted[0].summary



def test_pack_evidence_prefers_primary_case_page_marker_before_other_officials() -> None:
    findings = (
        ExtractedFinding(
            url='https://www.nik.gov.pl/plik/id,6423,vp,8193.pdf',
            title='FUNKCJONOWANIE SYSTEMU OCHRONY PRAW KLIENTÓW ...',
            summary='[official_subject:exact_subject] [exact_subject_content_lift:keep_exact_subject] broad official collateral',
        ),
        ExtractedFinding(
            url='https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html',
            title='Nierzetelny i nieprawidłowy nadzór KNF nad spółką GetBack S.A.',
            summary='[official_subject:exact_subject] [exact_subject_content_lift:prefer_primary_case_page] case page summary',
        ),
    )

    packed = _pack_evidence_for_synthesis(
        query='Co ustaliła NIK w sprawie nadzoru KNF nad spółką GetBack S.A.?',
        findings=findings,
    )

    assert packed.core
    assert packed.core[0].url == 'https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html'



def test_pack_evidence_promotes_primary_case_page_marker_to_core() -> None:
    findings = (
        ExtractedFinding(
            url='https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html',
            title='Nierzetelny i nieprawidłowy nadzór KNF nad spółką GetBack S.A.',
            summary='[official_subject:exact_subject] [exact_subject_content_lift:prefer_primary_case_page] case page summary',
        ),
        ExtractedFinding(
            url='https://www.nik.gov.pl/plik/id,6423,vp,8193.pdf',
            title='FUNKCJONOWANIE SYSTEMU OCHRONY PRAW KLIENTÓW ...',
            summary='[official_pdf_ingest:verified] broad collateral pdf',
            pdf_triage_notes='pdf_ingest_verified',
        ),
    )

    packed = _pack_evidence_for_synthesis(
        query='Co ustaliła NIK w sprawie nadzoru KNF nad spółką GetBack S.A.?',
        findings=findings,
    )

    assert packed.core
    assert packed.core[0].url == 'https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html'



def test_official_html_content_enricher_rewrites_exact_subject_summary() -> None:
    enricher = OfficialHtmlContentEnricher(
        lambda prompt: type('R', (), {'text': '{"summary":"NIK states the case concerns KNF oversight over GetBack and highlights concrete institutional failures.","confidence":0.88}'})(),
    )
    original = ExtractedFinding(
        url='https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html',
        title='Nierzetelny i nieprawidłowy nadzór KNF nad spółką GetBack S.A.',
        summary='[official_subject:exact_subject] teaser summary',
    )

    from sourcetrace.application import research_runtime as rr
    original_fetch = rr._fetch_html_article_text
    rr._fetch_html_article_text = lambda url, timeout_seconds=10.0, max_chars=12000: 'NIK states the case concerns KNF oversight over GetBack and highlights concrete institutional failures.'
    try:
        enriched = enricher.enrich(
            query='Co ustaliła NIK w sprawie nadzoru KNF nad spółką GetBack S.A.?',
            finding=original,
        )
    finally:
        rr._fetch_html_article_text = original_fetch

    assert enriched.html_content_enriched is True
    assert '[official_html_enriched]' in enriched.summary
    assert 'institutional failures' in enriched.summary


def test_live_progress_trace_preserves_exact_subject_state_after_html_enrichment() -> None:
    class GetBackExactSubjectSearch:
        def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
            del queries, round_number
            return (
                SearchHit(
                    url='https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html',
                    title='Wyniki kontroli NIK',
                    snippet='Oficjalny komunikat o wynikach kontroli.',
                ),
            )

    persistence = create_in_memory_research_persistence()
    manager = ResearchJobManager(persistence)
    judge = LlmOfficialSubjectPrecisionJudge(
        lambda prompt: type('R', (), {'text': '{"subject_match":"exact_subject","confidence":0.93,"reason":"Directly names GetBack and KNF oversight case."}'})()
    )
    enricher = OfficialHtmlContentEnricher(
        lambda prompt: type('R', (), {'text': '{"summary":"NIK states the case concerns KNF oversight over GetBack and highlights concrete institutional failures.","confidence":0.88}'})(),
    )
    worker = FakeResearchWorker(
        persistence,
        search=GetBackExactSubjectSearch(),
        subject_sheet_builder=lambda query, planning_analysis: None,
        official_subject_precision_judge=judge,
        official_html_content_enricher=enricher,
        stop_rails=type('OneRoundRails', (), {'should_stop': lambda self, **kwargs: True})(),
    )
    outcome = manager.start_job(
        ResearchJobStartRequest(
            owner_id='user-1',
            query='Co ustaliła NIK w sprawie nadzoru KNF nad spółką GetBack S.A.?',
        )
    )

    from sourcetrace.application import research_runtime as rr
    original_fetch = rr._fetch_html_article_text
    rr._fetch_html_article_text = lambda url, timeout_seconds=10.0, max_chars=12000: 'NIK states the case concerns KNF oversight over GetBack and highlights concrete institutional failures.'
    try:
        result = worker(outcome.job.job_id)
    finally:
        rr._fetch_html_article_text = original_fetch

    assert result is not None
    status = manager.get_job_status(outcome.job.job_id)
    assert status is not None

    extraction_event = next(
        event for event in status.progress
        if event.details is not None and event.details.get('stage') == 'extraction'
    )
    pack_event = next(
        event for event in status.progress
        if event.details is not None and event.details.get('stage') == 'evidence_pack'
    )

    extraction_trace = extraction_event.details['findings'][0]
    assert extraction_trace['subject_precision_label'] == 'exact_subject'
    assert extraction_trace['priority_band'] == 'exact_subject_winner'
    assert extraction_trace['html_content_enriched'] is True
    assert 'official_html_enriched' in extraction_trace['summary_markers']
    assert 'official_subject:exact_subject' not in extraction_trace['summary_markers']

    core_trace = pack_event.details['core'][0]
    assert core_trace['bucket'] == 'core'
    assert core_trace['subject_precision_label'] == 'exact_subject'
    assert core_trace['priority_band'] == 'exact_subject_winner'
    assert core_trace['exact_subject_priority_score'] >= 7
    assert 'official_html_enriched' in core_trace['summary_markers']



def test_enriched_exact_subject_priority_score_prefers_enriched_official_case_finding() -> None:
    finding = ExtractedFinding(
        url='https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html',
        title='Nierzetelny i nieprawidłowy nadzór KNF nad spółką GetBack S.A.',
        summary='[official_subject:exact_subject] [official_html_enriched] concrete case findings',
        html_content_enriched=True,
    )

    assert _enriched_exact_subject_priority_score(finding) >= 7



def test_top_findings_prefers_enriched_exact_subject_official_finding() -> None:
    findings = (
        ExtractedFinding(
            url='https://www.nik.gov.pl/plik/id,6423,vp,8193.pdf',
            title='FUNKCJONOWANIE SYSTEMU OCHRONY PRAW KLIENTÓW ...',
            summary='[official_pdf_ingest:verified] broad collateral pdf',
            pdf_triage_notes='pdf_ingest_verified',
        ),
        ExtractedFinding(
            url='https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html',
            title='Nierzetelny i nieprawidłowy nadzór KNF nad spółką GetBack S.A.',
            summary='[official_subject:exact_subject] [official_html_enriched] concrete case findings',
            html_content_enriched=True,
        ),
    )

    ranked = _top_findings(findings, limit=2, query='Co ustaliła NIK w sprawie nadzoru KNF nad spółką GetBack S.A.?')

    assert ranked[0].url == 'https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html'



def test_pack_evidence_promotes_enriched_exact_subject_official_finding_to_core() -> None:
    findings = (
        ExtractedFinding(
            url='https://www.nik.gov.pl/plik/id,6423,vp,8193.pdf',
            title='FUNKCJONOWANIE SYSTEMU OCHRONY PRAW KLIENTÓW ...',
            summary='[official_pdf_ingest:verified] broad collateral pdf',
            pdf_triage_notes='pdf_ingest_verified',
        ),
        ExtractedFinding(
            url='https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html',
            title='Nierzetelny i nieprawidłowy nadzór KNF nad spółką GetBack S.A.',
            summary='[official_subject:exact_subject] [official_html_enriched] concrete case findings',
            html_content_enriched=True,
        ),
    )

    packed = _pack_evidence_for_synthesis(
        query='Co ustaliła NIK w sprawie nadzoru KNF nad spółką GetBack S.A.?',
        findings=findings,
    )

    assert packed.core
    assert packed.core[0].url == 'https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html'



def test_structured_exact_subject_fields_survive_into_priority_score() -> None:
    finding = ExtractedFinding(
        url='https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html',
        title='Nierzetelny i nieprawidłowy nadzór KNF nad spółką GetBack S.A.',
        summary='plain enriched summary',
        html_content_enriched=True,
        subject_precision_label='exact_subject',
        priority_band='exact_subject_winner',
    )

    assert _enriched_exact_subject_priority_score(finding) >= 10



def test_pack_evidence_prefers_structured_exact_subject_winner_without_text_tags() -> None:
    findings = (
        ExtractedFinding(
            url='https://www.nik.gov.pl/plik/id,6423,vp,8193.pdf',
            title='FUNKCJONOWANIE SYSTEMU OCHRONY PRAW KLIENTÓW ...',
            summary='[official_pdf_ingest:verified] broad collateral pdf',
            pdf_triage_notes='pdf_ingest_verified',
        ),
        ExtractedFinding(
            url='https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html',
            title='Nierzetelny i nieprawidłowy nadzór KNF nad spółką GetBack S.A.',
            summary='concrete official case findings',
            html_content_enriched=True,
            subject_precision_label='exact_subject',
            priority_band='exact_subject_winner',
        ),
    )

    packed = _pack_evidence_for_synthesis(
        query='Co ustaliła NIK w sprawie nadzoru KNF nad spółką GetBack S.A.?',
        findings=findings,
    )

    assert packed.core
    assert packed.core[0].url == 'https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html'



def test_extracted_finding_can_store_structured_subject_trace_fields() -> None:
    finding = ExtractedFinding(
        url='https://example.test/getback',
        title='GetBack case',
        summary='summary',
        html_content_enriched=True,
        subject_precision_label='exact_subject',
        priority_band='exact_subject_winner',
    )

    assert finding.html_content_enriched is True
    assert finding.subject_precision_label == 'exact_subject'
    assert finding.priority_band == 'exact_subject_winner'



def test_source_type_classifies_nik_aktualnosci_article_as_official_docs() -> None:
    assert _source_type(
        'https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html',
        'Nierzetelny i nieprawidłowy nadzór KNF nad spółką GetBack S.A.',
    ) == 'official_docs'



def test_fake_research_worker_emits_pre_extraction_judge_activation_trace() -> None:
    persistence = create_in_memory_research_persistence()
    manager = ResearchJobManager(persistence)

    class Search:
        def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
            del queries, round_number
            return (
                SearchHit(
                    url='https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html',
                    title='Nierzetelny i nieprawidłowy nadzór KNF nad spółką GetBack S.A.',
                    snippet='Oficjalny komunikat NIK o ustaleniach dotyczących GetBack i KNF.',
                ),
            )

    judge = LlmOfficialSubjectPrecisionJudge(
        lambda prompt: type('R', (), {'text': '{"subject_match":"exact_subject","confidence":0.95,"reason":"Direct case page."}'})()
    )
    worker = FakeResearchWorker(
        persistence,
        search=Search(),
        official_subject_precision_judge=judge,
        stop_rails=type('OneRoundRails', (), {'should_stop': lambda self, **kwargs: True})(),
    )
    outcome = manager.start_job(
        ResearchJobStartRequest(owner_id='user-1', query='Co ustaliła NIK w sprawie nadzoru KNF nad spółką GetBack S.A.?')
    )

    worker(outcome.job.job_id)
    status = manager.get_job_status(outcome.job.job_id)
    assert status is not None
    pre = next(event for event in status.progress if (event.details or {}).get('stage') == 'pre_extraction_filter')
    trace = pre.details['judge_activation_trace']
    assert trace['judge_present'] is True
    assert trace['filtered_hit_count'] >= 1
    assert trace['official_candidate_count'] >= 1
    assert any(item['source_type'] == 'official_docs' for item in trace['candidate_source_types'])



def test_exact_subject_content_quality_score_prefers_rich_findings_over_teaser_pages() -> None:
    rich = ExtractedFinding(
        url='https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html',
        title='Nierzetelny i nieprawidłowy nadzór KNF nad spółką GetBack S.A.',
        summary='[official_html_enriched] NIK oceniła działania KNF negatywnie, wskazując nierzetelny i nieprawidłowy nadzór, zaniechania, brak reakcji, metodologię wyceny portfeli wierzytelności i straty obligatariuszy przekraczające 3,5 mld zł.',
        html_content_enriched=True,
        subject_precision_label='exact_subject',
        priority_band='exact_subject_winner',
    )
    teaser = ExtractedFinding(
        url='https://www.nik.gov.pl/kontrole/I/24/001/LBI',
        title='Nadzór Komisji Nadzoru Finansowego nad spółką Getback S.A. ...',
        summary='[official_html_enriched] Strona wskazuje numer kontroli i odsyła do skrótu prasowego i zapisu konferencji. Sam przytoczony tekst ma jednak charakter niemal wyłącznie nawigacyjno-teaserowy i nie zawiera merytorycznych ustaleń.',
        html_content_enriched=True,
        subject_precision_label='exact_subject',
        priority_band='exact_subject_winner',
    )
    assert _exact_subject_content_quality_score(rich) > _exact_subject_content_quality_score(teaser)


def test_pack_evidence_prefers_richer_exact_subject_official_page_over_teaser_page() -> None:
    teaser = ExtractedFinding(
        url='https://www.nik.gov.pl/kontrole/I/24/001/LBI',
        title='Nadzór Komisji Nadzoru Finansowego nad spółką Getback S.A. ...',
        summary='[official_html_enriched] Strona wskazuje numer kontroli i odsyła do skrótu prasowego i zapisu konferencji. Sam przytoczony tekst ma jednak charakter niemal wyłącznie nawigacyjno-teaserowy i nie zawiera merytorycznych ustaleń.',
        html_content_enriched=True,
        subject_precision_label='exact_subject',
        priority_band='exact_subject_winner',
    )
    rich = ExtractedFinding(
        url='https://www.nik.gov.pl/aktualnosci/nadzor-knf-nad-spolka-getback.html',
        title='Nierzetelny i nieprawidłowy nadzór KNF nad spółką GetBack S.A.',
        summary='[official_html_enriched] NIK oceniła działania KNF i UKNF negatywnie, wskazując nierzetelny i nieprawidłowy nadzór, zaniechania, brak reakcji, metodologię wyceny portfeli wierzytelności, sprawozdań finansowych i straty obligatariuszy przekraczające 3,5 mld zł.',
        html_content_enriched=True,
        subject_precision_label='exact_subject',
        priority_band='exact_subject_winner',
    )
    packed = _pack_evidence_for_synthesis(
        query='Co ustaliła NIK w sprawie nadzoru KNF nad spółką GetBack S.A.?',
        findings=(teaser, rich),
    )
    assert packed.core
    assert packed.core[0].url == rich.url
