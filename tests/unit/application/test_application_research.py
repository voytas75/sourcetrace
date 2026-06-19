from sourcetrace.application import (
    FakeResearchWorker,
    ResearchJobManager,
    ResearchJobStartRequest,
    SearchHit,
    build_research_execution,
)
from sourcetrace.domain import ResearchCompletionMode, ResearchJobStatus
from sourcetrace.storage import create_in_memory_research_persistence


class NoisyMarketSearch:
    def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
        if round_number == 1:
            return (
                SearchHit(
                    url="https://example.test/ethusdc-weekly",
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
    assert len(result.sources) == 2
    assert all("ethusdc" in source.title.lower() or "ethusdc" in source.url.lower() for source in result.sources)
    assert all("usdcad" not in source.title.lower() and "usdcad" not in source.url.lower() for source in result.sources)
    assert "physics" not in result.result.lower()
    assert "sociology" not in result.result.lower()
    assert "usdcad" not in result.result.lower()
