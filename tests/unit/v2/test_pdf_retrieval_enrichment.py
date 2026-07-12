from sourcetrace_v2.core.domain.models import PdfEvidenceContext, RetrievedEvidenceCandidate
from sourcetrace_v2.execution.stages.retrieval import (
    RetrievalStage,
    _looks_like_meaningful_pdf_snippet,
    _looks_like_pdf_candidate,
)


class _PdfGatewayRejected:
    def read(self, *, query: str, url: str, title: str, triage_verdict: str):
        from sourcetrace.application import PdfIngestResult
        return PdfIngestResult(
            relevant=False,
            confidence=0.2,
            document_scope="preview_only",
            entity_match_summary="Preview failed to verify full relevance",
            key_findings=(),
            evidence_pages=(),
        )


class _NoopSearch:
    def search(self, query: str):
        return ()


def test_pdf_candidate_keeps_pdf_context_when_snippet_is_meaningful_even_if_full_pdf_read_rejects() -> None:
    stage = RetrievalStage(search=_NoopSearch(), pdf=_PdfGatewayRejected())
    candidate = RetrievedEvidenceCandidate(
        candidate_id="c1",
        job_id="job-1",
        run_id="run-1",
        provider="searxng",
        query="hybrid remote work poland pdf",
        title="[PDF] The Determinants of Remote Work in Poland",
        url="https://example.test/doc.pdf",
        snippet="Main findings: Remote work, in particular hybrid work, is likely to become more common in enterprises and employers need to verify the results of remote work.",
        rank=1,
    )

    enriched = stage._enrich_pdf_candidates(candidates=(candidate,), query="hybrid remote work poland pdf")

    assert enriched[0].pdf_context == PdfEvidenceContext(
        document_scope="preview_only",
        entity_match_summary="Preview failed to verify full relevance",
        key_findings=(),
    )


class _PdfGatewayRejectedWithPartialFindings:
    def read(self, *, query: str, url: str, title: str, triage_verdict: str):
        from sourcetrace.application import PdfIngestResult
        return PdfIngestResult(
            relevant=False,
            confidence=0.42,
            document_scope="Polish labour law guidance for hybrid remote work",
            entity_match_summary="Poland labour-market employers",
            key_findings=("Hybrid remote work in Poland requires employer work rules alignment.",),
            evidence_pages=(3,),
        )


class _PdfGatewayRejectedWithFailureOnly:
    def read(self, *, query: str, url: str, title: str, triage_verdict: str):
        from sourcetrace.application import PdfIngestResult
        return PdfIngestResult(
            relevant=False,
            confidence=0.2,
            document_scope="preview_only",
            entity_match_summary="Full read failed after positive preview: RuntimeError",
            key_findings=(),
            evidence_pages=(1,),
        )


class _PdfGatewayRejectedWithoutContext:
    def read(self, *, query: str, url: str, title: str, triage_verdict: str):
        from sourcetrace.application import PdfIngestResult
        return PdfIngestResult(
            relevant=False,
            confidence=0.24,
            document_scope="",
            entity_match_summary="",
            key_findings=(),
            evidence_pages=(),
        )


def test_pdf_candidate_keeps_partial_pdf_context_when_pdf_read_returns_meaningful_findings_but_search_snippet_is_thin() -> None:
    stage = RetrievalStage(search=_NoopSearch(), pdf=_PdfGatewayRejectedWithPartialFindings())
    candidate = RetrievedEvidenceCandidate(
        candidate_id="c1",
        job_id="job-1",
        run_id="run-1",
        provider="searxng",
        query="hybrid remote work poland pdf",
        title="[PDF] Hybrid remote work in Poland",
        url="https://example.test/doc.pdf",
        snippet="PDF result",
        rank=1,
    )

    enriched = stage._enrich_pdf_candidates(candidates=(candidate,), query="hybrid remote work poland pdf")

    assert enriched[0].pdf_context == PdfEvidenceContext(
        document_scope="Polish labour law guidance for hybrid remote work",
        entity_match_summary="Poland labour-market employers",
        key_findings=("Hybrid remote work in Poland requires employer work rules alignment.",),
    )


def test_pdf_candidate_does_not_keep_pdf_context_when_only_failure_metadata_is_available_and_search_snippet_is_thin() -> None:
    stage = RetrievalStage(search=_NoopSearch(), pdf=_PdfGatewayRejectedWithFailureOnly())
    candidate = RetrievedEvidenceCandidate(
        candidate_id="c1",
        job_id="job-1",
        run_id="run-1",
        provider="searxng",
        query="hybrid remote work poland pdf",
        title="[PDF] Hybrid remote work in Poland",
        url="https://example.test/doc.pdf",
        snippet="PDF result",
        rank=1,
    )

    enriched = stage._enrich_pdf_candidates(candidates=(candidate,), query="hybrid remote work poland pdf")

    assert enriched[0].pdf_context is None


def test_pdf_candidate_salvages_snippet_only_pdf_context_for_strong_community_outcome_snippet() -> None:
    stage = RetrievalStage(search=_NoopSearch(), pdf=_PdfGatewayRejectedWithoutContext())
    candidate = RetrievedEvidenceCandidate(
        candidate_id="c1",
        job_id="job-1",
        run_id="run-1",
        provider="searxng",
        query="What are the main findings in PDF reports about the quality of life of the Polish diaspora in Germany?",
        title="[PDF] German and Polish Perspectives on Migration, Refugee and Border ...",
        url="https://example.test/migration-report.pdf",
        snippet=(
            "The report examines the Polish diaspora in Germany and highlights employment, healthcare, education, "
            "and housing conditions alongside broader integration pressures affecting everyday quality of life."
        ),
        rank=1,
    )

    enriched = stage._enrich_pdf_candidates(candidates=(candidate,), query=candidate.query)

    assert enriched[0].pdf_context == PdfEvidenceContext(
        document_scope="Snippet-only PDF signal; full-document relevance not verified.",
        entity_match_summary=(
            "Snippet-only partial match for queried community outcomes: employment, healthcare, "
            "education, housing."
        ),
        key_findings=(
            "Search snippet mentions employment, healthcare, education, housing for the queried "
            "community/topic; full-PDF findings were not verified.",
        ),
    )


def test_pdf_candidate_does_not_salvage_snippet_only_pdf_context_for_thin_generic_snippet() -> None:
    stage = RetrievalStage(search=_NoopSearch(), pdf=_PdfGatewayRejectedWithoutContext())
    candidate = RetrievedEvidenceCandidate(
        candidate_id="c1",
        job_id="job-1",
        run_id="run-1",
        provider="searxng",
        query="What are the main findings in PDF reports about the quality of life of the Polish diaspora in Germany?",
        title="[PDF] Migration and diaspora overview",
        url="https://example.test/diaspora-overview.pdf",
        snippet="Overview of the Polish diaspora in Germany.",
        rank=1,
    )

    enriched = stage._enrich_pdf_candidates(candidates=(candidate,), query=candidate.query)

    assert enriched[0].pdf_context is None


def test_pdf_candidate_does_not_salvage_snippet_only_pdf_context_for_failure_sludge_snippet() -> None:
    stage = RetrievalStage(search=_NoopSearch(), pdf=_PdfGatewayRejectedWithoutContext())
    candidate = RetrievedEvidenceCandidate(
        candidate_id="c1",
        job_id="job-1",
        run_id="run-1",
        provider="searxng",
        query="What are the main findings in PDF reports about the quality of life of the Polish diaspora in Germany?",
        title="[PDF] Migration and diaspora overview",
        url="https://example.test/diaspora-overview.pdf",
        snippet=(
            "Preview failed to load the PDF, but the result card mentions employment, healthcare, education, and "
            "housing for the Polish diaspora in Germany while the full read failed and no clear subject match was returned."
        ),
        rank=1,
    )

    enriched = stage._enrich_pdf_candidates(candidates=(candidate,), query=candidate.query)

    assert enriched[0].pdf_context is None



def test_pdf_candidate_detection_accepts_pdf_paths_with_trailing_segments_and_pdf_prefix_title() -> None:
    candidate = RetrievedEvidenceCandidate(
        candidate_id="c1",
        job_id="job-1",
        run_id="run-1",
        provider="searxng",
        query="query",
        title="[PDF] German and Polish Perspectives on Migration, Refugee and Border ...",
        url="https://inp.uj.edu.pl/documents/3905854/155738525/German+and+Polish+Perspectives-2025.pdf/9323cfea-cc1e-4d50-8eae-44a0e272dfef",
        snippet="snippet",
        rank=1,
    )

    assert _looks_like_pdf_candidate(candidate) is True


def test_meaningful_pdf_snippet_does_not_treat_topic_phrases_as_findings_markers() -> None:
    snippet = (
        "This preview discusses remote work and hybrid work across employers, scheduling models, and policy choices "
        "using descriptive overview language only and never surfacing any concrete evidence section or measured outcome."
    )

    assert _looks_like_meaningful_pdf_snippet(snippet) is False


def test_meaningful_pdf_snippet_still_accepts_generic_research_markers() -> None:
    snippet = (
        "Abstract: This study reports results from 412 respondents and compares employer practices across several "
        "operating models with a concise conclusion section."
    )

    assert _looks_like_meaningful_pdf_snippet(snippet) is True
