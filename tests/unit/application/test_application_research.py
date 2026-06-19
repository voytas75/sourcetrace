from sourcetrace.application import (
    ExtractedFinding,
    FakeResearchWorker,
    ResearchJobManager,
    ResearchJobStartRequest,
    StubExtractor,
    StubQueryGenerator,
    SearchHit,
    build_research_execution,
)
from sourcetrace.application.research_runtime import _is_relevant_hit, _looks_like_listing_page, _top_findings
from sourcetrace.domain import ResearchCompletionMode, ResearchJobStatus
from sourcetrace.storage import create_in_memory_research_persistence


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
    persistence = create_in_memory_research_persistence()
    manager = ResearchJobManager(persistence)
    worker = FakeResearchWorker(persistence)
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


def test_fake_research_worker_can_save_partial_salvage_result() -> None:
    persistence = create_in_memory_research_persistence()
    manager = ResearchJobManager(persistence)
    worker = FakeResearchWorker(persistence)
    outcome = manager.start_job(
        ResearchJobStartRequest(owner_id="user-1", query="deep research architecture")
    )

    result = worker.save_partial_result(outcome.job.job_id)

    assert result is not None
    assert result.completion_mode is ResearchCompletionMode.PARTIAL_ERROR
    assert manager.get_job_result(outcome.job.job_id).result is not None


def test_build_research_execution_wires_runtime_bundle() -> None:
    execution = build_research_execution()
    accepted = execution.start_job(
        ResearchJobStartRequest(owner_id="user-1", query="deep research architecture")
    )
    status = execution.get_job_status(accepted.job.job_id)

    assert status is not None
    assert status.job.job_id == accepted.job.job_id


def test_fake_research_worker_runs_two_round_engine_loop() -> None:
    persistence = create_in_memory_research_persistence()
    manager = ResearchJobManager(persistence)
    worker = FakeResearchWorker(persistence)
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
    assert _is_relevant_hit(query=query, hit=strong_doc) is True


def test_top_findings_prefers_official_docs_over_blog_and_video_for_procedural_query() -> None:
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
    )

    top = _top_findings(
        findings,
        limit=2,
        query="jak działa configuration baseline w sccm po wdrożeniu na kolekcję komputerów",
    )

    assert len(top) == 2
    assert top[0].url.startswith("https://learn.microsoft.com/")
    assert all("youtube.com" not in finding.url for finding in top)
