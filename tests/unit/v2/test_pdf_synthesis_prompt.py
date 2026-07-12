from sourcetrace_v2.app.services.execution import _build_synthesis_prompt
from sourcetrace_v2.core.domain.models import PdfEvidenceContext, RetrievedEvidenceCandidate


def test_synthesis_prompt_prefers_pdf_evidence_and_forbids_upload_redirect() -> None:
    candidate = RetrievedEvidenceCandidate(
        candidate_id="c1",
        job_id="job-1",
        run_id="run-1",
        provider="searxng",
        query="hybrid remote work pdf",
        title="[PDF] Remote Work and Work Efficiency",
        url="https://example.test/doc.pdf",
        snippet="Snippet about remote work efficiency.",
        rank=1,
        pdf_context=PdfEvidenceContext(
            document_scope="Remote Work and Work Efficiency",
            entity_match_summary="Work Efficiency",
            key_findings=(
                "Remote work improved perceived flexibility.",
                "Hybrid arrangements reduced commuting burden.",
            ),
        ),
    )

    prompt = _build_synthesis_prompt(
        seed_text="What are the main findings in the PDF document about hybrid remote work in Poland?",
        evidence_query="hybrid remote work Poland pdf",
        evidence_candidates=(candidate,),
    )

    assert "If PDF context is present, summarize the concrete PDF-derived findings first" in prompt
    assert "Do not ask the user to upload a PDF" in prompt
    assert "pdf_finding: Remote work improved perceived flexibility." in prompt
    assert "pdf_finding: Hybrid arrangements reduced commuting burden." in prompt
