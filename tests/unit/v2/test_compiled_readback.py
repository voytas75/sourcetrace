import json

from sourcetrace_v2.app.composition.runtime import build_stubbed_memory_runtime
from sourcetrace_v2.app.services.compiled_readback import load_persisted_compiled_artifact_view
from sourcetrace_v2.app.services.http_api import (
    handle_get_persisted_compiled_artifact_request,
    handle_run_minimal_flow_request,
)
from sourcetrace_v2.core.contracts.compiled_artifacts import CompiledEvidenceSnapshot, CompiledResearchArtifact, PdfEvidenceContextSnapshot
from sourcetrace_v2.core.domain.models import ResearchResultArtifact, RunPersistenceMarker
from sourcetrace_v2.projections.api.compiled_readback import project_persisted_compiled_artifact_view


def test_project_persisted_compiled_artifact_view_returns_found_shape() -> None:
    runtime = build_stubbed_memory_runtime()
    handle_run_minimal_flow_request(
        job_id="job-compiled-readback",
        run_id="run-compiled-readback",
        seed_text="test query",
        runtime=runtime,
    )

    view = load_persisted_compiled_artifact_view(
        job_id="job-compiled-readback",
        run_id="run-compiled-readback",
        results=runtime.results,
    )
    payload = project_persisted_compiled_artifact_view(view=view)

    assert payload["status"] == "found"
    assert payload["persistence"]["completeness"] == "complete"
    assert payload["persistence"]["compiled_artifact_present"] is True
    assert payload["compiled_artifact"]["present"] is True


def test_compiled_artifact_http_returns_404_when_absent() -> None:
    runtime = build_stubbed_memory_runtime()

    response = handle_get_persisted_compiled_artifact_request(
        job_id="missing-job",
        run_id="missing-run",
        runtime=runtime,
    )
    payload = json.loads(response.body)

    assert response.status_code == 404
    assert payload["status"] == "not_found"
    assert payload["compiled_artifact"]["present"] is False


def test_compiled_artifact_http_returns_202_for_partial_paths() -> None:
    runtime = build_stubbed_memory_runtime()
    runtime.results.save_compiled_artifact(
        CompiledResearchArtifact(
            artifact_id="compiled:job-partial:run-partial",
            job_id="job-partial",
            run_id="run-partial",
            summary="partial compiled",
        )
    )
    runtime.results.save_run_marker(
        RunPersistenceMarker(job_id="job-marker-only", run_id="run-marker-only")
    )
    runtime.results.save_result(
        ResearchResultArtifact(job_id="job-result-only", run_id="run-result-only", result_text="result only")
    )

    compiled_only = handle_get_persisted_compiled_artifact_request(
        job_id="job-partial",
        run_id="run-partial",
        runtime=runtime,
    )
    compiled_only_payload = json.loads(compiled_only.body)
    assert compiled_only.status_code == 202
    assert compiled_only_payload["status"] == "incomplete"
    assert compiled_only_payload["persistence"]["compiled_artifact_present"] is True
    assert compiled_only_payload["persistence"]["run_artifact_present"] is False

    marker_only = handle_get_persisted_compiled_artifact_request(
        job_id="job-marker-only",
        run_id="run-marker-only",
        runtime=runtime,
    )
    marker_only_payload = json.loads(marker_only.body)
    assert marker_only.status_code == 202
    assert marker_only_payload["status"] == "incomplete"
    assert marker_only_payload["persistence"]["compiled_artifact_present"] is False
    assert marker_only_payload["persistence"]["marker_present"] is True

    result_only = handle_get_persisted_compiled_artifact_request(
        job_id="job-result-only",
        run_id="run-result-only",
        runtime=runtime,
    )
    result_only_payload = json.loads(result_only.body)
    assert result_only.status_code == 202
    assert result_only_payload["status"] == "incomplete"
    assert result_only_payload["persistence"]["compiled_artifact_present"] is False
    assert result_only_payload["persistence"]["run_artifact_present"] is True


def test_compiled_artifact_readback_preserves_judgment_contract_payload() -> None:
    runtime = build_stubbed_memory_runtime()
    handle_run_minimal_flow_request(
        job_id="job-compiled-judgment",
        run_id="run-compiled-judgment",
        seed_text="official tax filing deadline guidance",
        runtime=runtime,
    )

    response = handle_get_persisted_compiled_artifact_request(
        job_id="job-compiled-judgment",
        run_id="run-compiled-judgment",
        runtime=runtime,
    )
    payload = json.loads(response.body)

    assert response.status_code == 200
    assert payload["compiled_artifact"]["selected_evidence_contract_version"] == "authority-relevance-judgment-contract-v1"
    selected = payload["compiled_artifact"]["selected_evidence"]
    assert len(selected) == 2
    first = selected[0]["judgment"]
    assert first["contract_version"] == "authority-relevance-judgment-contract-v1"
    assert set(first.keys()) == {"contract_version", "authority", "topic_match", "specificity", "answer_fit"}
    assert first["authority"]["band"] in {"none", "low", "medium", "high"}
    assert isinstance(first["authority"]["signals"], list)
    assert first["answer_fit"]["score"] >= 0


def test_compiled_artifact_readback_preserves_typed_pdf_context_payload() -> None:
    runtime = build_stubbed_memory_runtime()
    runtime.results.save_compiled_artifact(
        CompiledResearchArtifact(
            artifact_id="compiled:job-pdf-context:run-pdf-context",
            job_id="job-pdf-context",
            run_id="run-pdf-context",
            summary="compiled with typed pdf context",
            selected_evidence=(
                CompiledEvidenceSnapshot(
                    title="Raport NIK.pdf",
                    url="https://example.test/raport.pdf",
                    provider="stub-search",
                    rank=1,
                    snippet="pdf_scope=NIK official control document | Szpital Południowy w Warszawie | Ustalenie 1",
                    pdf_context=PdfEvidenceContextSnapshot(
                        document_scope="NIK official control document",
                        entity_match_summary="Szpital Południowy w Warszawie",
                        key_findings=("Ustalenie 1", "Ustalenie 2"),
                    ),
                ),
            ),
        )
    )
    runtime.results.save_result(
        ResearchResultArtifact(
            job_id="job-pdf-context",
            run_id="run-pdf-context",
            result_text="result",
        )
    )
    runtime.results.save_run_marker(
        RunPersistenceMarker(job_id="job-pdf-context", run_id="run-pdf-context")
    )

    response = handle_get_persisted_compiled_artifact_request(
        job_id="job-pdf-context",
        run_id="run-pdf-context",
        runtime=runtime,
    )
    payload = json.loads(response.body)

    assert response.status_code == 200
    selected = payload["compiled_artifact"]["selected_evidence"]
    assert len(selected) == 1
    pdf_context = selected[0]["pdf_context"]
    assert pdf_context is not None
    assert pdf_context["document_scope"] == "NIK official control document"
    assert pdf_context["entity_match_summary"] == "Szpital Południowy w Warszawie"
    assert pdf_context["key_findings"] == ["Ustalenie 1", "Ustalenie 2"]
