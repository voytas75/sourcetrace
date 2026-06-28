from sourcetrace_v2.adapters.storage.jsonl import JsonlResultArtifactRepository
from sourcetrace_v2.core.contracts.compiled_artifacts import CompiledEvidenceSnapshot, CompiledResearchArtifact, PdfEvidenceContextSnapshot
from sourcetrace_v2.core.domain.models import PdfEvidenceContext, ResearchResultArtifact, RetrievedEvidenceCandidate


def test_jsonl_roundtrip_preserves_pdf_context_on_result_and_compiled_artifact(tmp_path) -> None:
    repo = JsonlResultArtifactRepository(tmp_path)

    result = ResearchResultArtifact(
        job_id="job-jsonl-pdf",
        run_id="run-jsonl-pdf",
        result_text="answer",
        summary="summary",
        evidence_query="query",
        evidence_candidates=(
            RetrievedEvidenceCandidate(
                candidate_id="cand-1",
                job_id="job-jsonl-pdf",
                run_id="run-jsonl-pdf",
                provider="stub-search",
                query="query",
                title="Official PDF",
                url="https://example.test/report.pdf",
                snippet="pdf_scope=NIK official control document",
                rank=1,
                pdf_context=PdfEvidenceContext(
                    document_scope="NIK official control document",
                    entity_match_summary="Szpital Południowy w Warszawie",
                    key_findings=("Ustalenie 1",),
                ),
            ),
        ),
    )
    compiled = CompiledResearchArtifact(
        artifact_id="compiled:job-jsonl-pdf:run-jsonl-pdf",
        job_id="job-jsonl-pdf",
        run_id="run-jsonl-pdf",
        summary="summary",
        selected_evidence=(
            CompiledEvidenceSnapshot(
                title="Official PDF",
                url="https://example.test/report.pdf",
                provider="stub-search",
                rank=1,
                snippet="pdf_scope=NIK official control document",
                pdf_context=PdfEvidenceContextSnapshot(
                    document_scope="NIK official control document",
                    entity_match_summary="Szpital Południowy w Warszawie",
                    key_findings=("Ustalenie 1",),
                ),
            ),
        ),
        selected_evidence_contract_version=None,
    )

    repo.save_result(result)
    repo.save_compiled_artifact(compiled)

    loaded_result = repo.get_result(job_id="job-jsonl-pdf", run_id="run-jsonl-pdf")
    loaded_compiled = repo.get_compiled_artifact(job_id="job-jsonl-pdf", run_id="run-jsonl-pdf")

    assert loaded_result is not None
    assert loaded_result.evidence_candidates[0].pdf_context is not None
    assert loaded_result.evidence_candidates[0].pdf_context.document_scope == "NIK official control document"
    assert loaded_result.evidence_candidates[0].pdf_context.key_findings == ("Ustalenie 1",)

    assert loaded_compiled is not None
    assert loaded_compiled.selected_evidence[0].pdf_context is not None
    assert loaded_compiled.selected_evidence[0].pdf_context.entity_match_summary == "Szpital Południowy w Warszawie"
    assert loaded_compiled.selected_evidence[0].pdf_context.key_findings == ("Ustalenie 1",)
