from sourcetrace_v2.app.composition.runtime import build_stubbed_memory_runtime
from sourcetrace_v2.app.services.http_api import handle_run_minimal_flow_request
from sourcetrace_v2.app.services.readback import load_persisted_execution_view
from sourcetrace_v2.core.contracts.read_models import PersistedViewStatus, PersistenceCompleteness
from sourcetrace_v2.core.domain.models import ResearchResultArtifact, RunPersistenceMarker


def test_load_persisted_execution_view_roundtrip() -> None:
    runtime = build_stubbed_memory_runtime()
    handle_run_minimal_flow_request(
        job_id="job-readback",
        run_id="run-readback",
        seed_text="please use fallback",
        runtime=runtime,
    )

    view = load_persisted_execution_view(
        job_id="job-readback",
        run_id="run-readback",
        results=runtime.results,
        receipts=runtime.receipts,
    )

    assert view.status == PersistedViewStatus.FOUND
    assert view.artifact is not None
    assert view.marker is not None
    assert view.artifact.job_id == "job-readback"
    assert view.artifact.run_id == "run-readback"
    assert view.envelope.job_id == "job-readback"
    assert view.envelope.run_id == "run-readback"
    assert view.envelope.persistence_completeness == PersistenceCompleteness.COMPLETE
    assert view.envelope.artifact_present is True
    assert view.envelope.marker_present is True
    assert view.envelope.marker_state == "committed"
    assert view.rollup.llm_calls == 4
    assert view.rollup.total_tokens == 384
    assert view.rollup.degraded_calls == 4
    assert len(view.stage_receipts) == 10
    assert len(view.llm_receipts) == 4


def test_load_persisted_execution_view_is_incomplete_without_marker() -> None:
    runtime = build_stubbed_memory_runtime()
    runtime.results.save_result(ResearchResultArtifact(job_id="job-no-marker", run_id="run-no-marker", result_text="x"))

    view = load_persisted_execution_view(
        job_id="job-no-marker",
        run_id="run-no-marker",
        results=runtime.results,
        receipts=runtime.receipts,
    )

    assert view.status == PersistedViewStatus.INCOMPLETE
    assert view.envelope.persistence_completeness == PersistenceCompleteness.PARTIAL
    assert view.envelope.artifact_present is True
    assert view.envelope.marker_present is False
    assert view.envelope.marker_state is None
    assert view.artifact is not None
    assert view.marker is None


def test_load_persisted_execution_view_is_incomplete_with_marker_only() -> None:
    runtime = build_stubbed_memory_runtime()
    runtime.results.save_run_marker(RunPersistenceMarker(job_id="job-marker-only", run_id="run-marker-only"))

    view = load_persisted_execution_view(
        job_id="job-marker-only",
        run_id="run-marker-only",
        results=runtime.results,
        receipts=runtime.receipts,
    )

    assert view.status == PersistedViewStatus.INCOMPLETE
    assert view.envelope.persistence_completeness == PersistenceCompleteness.PARTIAL
    assert view.envelope.artifact_present is False
    assert view.envelope.marker_present is True
    assert view.envelope.marker_state == "committed"
    assert view.artifact is None
    assert view.marker is not None


def test_load_persisted_execution_view_is_absent_when_nothing_was_persisted() -> None:
    runtime = build_stubbed_memory_runtime()

    view = load_persisted_execution_view(
        job_id="job-missing",
        run_id="run-missing",
        results=runtime.results,
        receipts=runtime.receipts,
    )

    assert view.status == PersistedViewStatus.NOT_FOUND
    assert view.envelope.persistence_completeness == PersistenceCompleteness.ABSENT
    assert view.envelope.artifact_present is False
    assert view.envelope.marker_present is False
    assert view.envelope.marker_state is None
