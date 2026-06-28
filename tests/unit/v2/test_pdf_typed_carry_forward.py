from sourcetrace_v2.app.services.compiled_artifacts import build_compiled_artifact
from sourcetrace_v2.core.domain.models import PdfEvidenceContext, ResearchResultArtifact, RetrievedEvidenceCandidate
from sourcetrace_v2.projections.api.compiled_artifacts import project_compiled_artifact


def test_pdf_context_is_carried_into_compiled_artifact_projection() -> None:
    artifact = ResearchResultArtifact(
        job_id="job-pdf-typed",
        run_id="run-pdf-typed",
        result_text="answer",
        summary="summary",
        evidence_query="query",
        evidence_candidates=(
            RetrievedEvidenceCandidate(
                candidate_id="cand-1",
                job_id="job-pdf-typed",
                run_id="run-pdf-typed",
                provider="stub-search",
                query="query",
                title="Official PDF",
                url="https://example.test/report.pdf",
                snippet="pdf_scope=NIK official control document | Szpital Południowy w Warszawie | Ustalenie 1",
                rank=1,
                pdf_context=PdfEvidenceContext(
                    document_scope="NIK official control document",
                    entity_match_summary="Szpital Południowy w Warszawie",
                    key_findings=("Ustalenie 1", "Ustalenie 2"),
                ),
            ),
        ),
    )

    compiled = build_compiled_artifact(artifact=artifact)
    payload = project_compiled_artifact(artifact=compiled)

    pdf_context = payload["selected_evidence"][0]["pdf_context"]
    assert pdf_context is not None
    assert pdf_context["document_scope"] == "NIK official control document"
    assert pdf_context["entity_match_summary"] == "Szpital Południowy w Warszawie"
    assert pdf_context["key_findings"] == ["Ustalenie 1", "Ustalenie 2"]
