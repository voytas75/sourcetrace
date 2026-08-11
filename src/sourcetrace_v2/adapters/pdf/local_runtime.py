from sourcetrace_pdf_runtime.analyzer import build_research_pdf_analyzer
from sourcetrace_pdf_runtime.capability import openclaw_pdf_capability
from sourcetrace_v2.adapters.pdf.interfaces import PdfReadResult
from sourcetrace_v2.adapters.pdf.runtime_ingest import RuntimePdfReadGateway


def build_local_pdf_read_gateway() -> RuntimePdfReadGateway:
    analyzer = build_research_pdf_analyzer(openclaw_pdf_capability)

    def as_v2_result(*, query: str, url: str, title: str, triage_verdict: str) -> PdfReadResult:
        result = analyzer(
            query=query,
            url=url,
            title=title,
            triage_verdict=triage_verdict,
        )
        return PdfReadResult(
            relevant=result.relevant,
            confidence=result.confidence,
            document_scope=result.document_scope,
            entity_match_summary=result.entity_match_summary,
            key_findings=result.key_findings,
            evidence_pages=result.evidence_pages,
        )

    return RuntimePdfReadGateway(analyzer=as_v2_result)
