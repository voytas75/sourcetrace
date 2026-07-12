import pytest

from sourcetrace_v2.core.domain.models import PdfEvidenceContext, RetrievedEvidenceCandidate
from sourcetrace_v2.core.policies.selected_evidence import decide_selected_evidence


pytestmark = pytest.mark.xfail(reason="future policy coverage for non-SSOT selected_evidence bias", strict=False)


def test_pdf_query_bias_prefers_pdf_candidate_with_context_over_generic_high_authority_surface() -> None:
    generic = RetrievedEvidenceCandidate(
        candidate_id="c1",
        job_id="job-1",
        run_id="run-1",
        provider="searxng",
        query="pdf document findings hybrid remote work poland",
        title="Psychosocial working conditions and mental well-being",
        url="https://pmc.ncbi.nlm.nih.gov/articles/PMC12064348/",
        snippet="The Act provides for both total remote work and hybrid remote work partly at home and partly at a company.",
        rank=1,
        source_type="institutional",
    )
    topical_pdf = RetrievedEvidenceCandidate(
        candidate_id="c2",
        job_id="job-1",
        run_id="run-1",
        provider="searxng",
        query="pdf document findings hybrid remote work poland",
        title="[PDF] Hybrid Remote Work: Social and Legal Aspects",
        url="https://example.test/hybrid-remote-work.pdf",
        snippet="Main findings: hybrid remote work was introduced into the Polish legal system and analyzed in social and legal terms.",
        rank=3,
        source_type="unknown",
        pdf_context=PdfEvidenceContext(
            document_scope="Hybrid Remote Work: Social and Legal Aspects",
            entity_match_summary="Hybrid Remote Work",
            key_findings=("Hybrid remote work was introduced into the Polish legal system.",),
        ),
    )

    decision = decide_selected_evidence((generic, topical_pdf), limit=1)

    assert decision.selected == (topical_pdf,)


def test_pdf_query_bias_prefers_candidate_matching_rarest_explicit_focus_token() -> None:
    generic_global_pdf = RetrievedEvidenceCandidate(
        candidate_id="c3",
        job_id="job-2",
        run_id="run-2",
        provider="searxng",
        query="pdf findings hybrid remote work Poland",
        title="[PDF] Hybrid remote work findings and legal implications",
        url="https://pmc.ncbi.nlm.nih.gov/articles/PMC99999999/pdf/",
        snippet="Global findings on hybrid remote work and legal implications across large employers.",
        rank=1,
        source_type="institutional",
        pdf_context=PdfEvidenceContext(
            document_scope="Hybrid remote work findings and legal implications",
            entity_match_summary="Hybrid remote work findings",
            key_findings=("The report compares hybrid remote work practices across large employers.",),
        ),
    )
    poland_specific_pdf = RetrievedEvidenceCandidate(
        candidate_id="c4",
        job_id="job-2",
        run_id="run-2",
        provider="searxng",
        query="pdf findings hybrid remote work Poland",
        title="[PDF] Hybrid remote work in Poland: legal implications",
        url="https://example.test/hybrid-remote-work-poland.pdf",
        snippet="Findings focused on hybrid remote work in Poland and the local legal framework.",
        rank=2,
        source_type="unknown",
        pdf_context=PdfEvidenceContext(
            document_scope="Hybrid remote work in Poland: legal implications",
            entity_match_summary="Hybrid remote work in Poland",
            key_findings=("The report focuses on hybrid remote work in Poland and local employer duties.",),
        ),
    )

    decision = decide_selected_evidence((generic_global_pdf, poland_specific_pdf), limit=1)

    assert decision.selected == (poland_specific_pdf,)


def test_article_findings_query_prefers_locale_specific_article_over_generic_global_article() -> None:
    generic_global_article = RetrievedEvidenceCandidate(
        candidate_id="c5",
        job_id="job-3",
        run_id="run-3",
        provider="searxng",
        query="article findings hybrid remote work Poland",
        title="Hybrid remote work findings and legal implications",
        url="https://pmc.ncbi.nlm.nih.gov/articles/PMC88888888/",
        snippet="Article findings on hybrid remote work and legal implications across major markets.",
        rank=1,
        source_type="institutional",
    )
    poland_specific_article = RetrievedEvidenceCandidate(
        candidate_id="c6",
        job_id="job-3",
        run_id="run-3",
        provider="searxng",
        query="article findings hybrid remote work Poland",
        title="Hybrid remote work in Poland and legal implications",
        url="https://example.test/articles/hybrid-remote-work-poland",
        snippet="Article on hybrid remote work in Poland and the related local legal implications.",
        rank=2,
        source_type="unknown",
    )

    decision = decide_selected_evidence((generic_global_article, poland_specific_article), limit=1)

    assert decision.selected == (poland_specific_article,)
