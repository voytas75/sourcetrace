from sourcetrace.application import PdfIngestResult
from sourcetrace_pdf_runtime.analyzer import (
    RuntimePdfCapability,
    coerce_float,
    coerce_positive_ints,
    coerce_strings,
    parse_full_confidence,
    parse_full_entity_match,
    parse_full_evidence_pages,
    parse_full_key_findings,
    parse_full_relevant,
    parse_full_scope,
    parse_preview_candidate_pages,
    parse_preview_confidence,
    parse_preview_entity_match,
    parse_preview_relevance,
    parse_preview_scope,
)
from sourcetrace_pdf_runtime.analyzer import (
    build_research_pdf_analyzer as build_neutral_pdf_analyzer,
)
from sourcetrace_pdf_runtime.models import PdfAnalysisResult


def _as_legacy_result(result: PdfAnalysisResult) -> PdfIngestResult:
    return PdfIngestResult(
        relevant=result.relevant,
        confidence=result.confidence,
        document_scope=result.document_scope,
        entity_match_summary=result.entity_match_summary,
        key_findings=result.key_findings,
        evidence_pages=result.evidence_pages,
    )


def build_research_pdf_analyzer(pdf_capability: RuntimePdfCapability):
    analyzer = build_neutral_pdf_analyzer(pdf_capability)

    def research_pdf_analyzer(*, query: str, url: str, title: str, triage_verdict: str) -> PdfIngestResult:
        return _as_legacy_result(
            analyzer(
                query=query,
                url=url,
                title=title,
                triage_verdict=triage_verdict,
            )
        )

    return research_pdf_analyzer


_coerce_float = coerce_float
_coerce_positive_ints = coerce_positive_ints
_coerce_strings = coerce_strings


__all__ = [
    "RuntimePdfCapability",
    "build_research_pdf_analyzer",
    "parse_full_confidence",
    "parse_full_entity_match",
    "parse_full_evidence_pages",
    "parse_full_key_findings",
    "parse_full_relevant",
    "parse_full_scope",
    "parse_preview_candidate_pages",
    "parse_preview_confidence",
    "parse_preview_entity_match",
    "parse_preview_relevance",
    "parse_preview_scope",
]
