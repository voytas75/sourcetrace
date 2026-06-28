from __future__ import annotations

from typing import Any, Callable

from sourcetrace_v2.adapters.pdf.interfaces import PdfReadGateway, PdfReadResult


class RuntimePdfReadGateway(PdfReadGateway):
    """Thin v2 adapter around an external runtime PDF analyzer callback."""

    def __init__(self, *, analyzer: Callable[..., object]) -> None:
        self._analyzer = analyzer

    def read(
        self,
        *,
        query: str,
        url: str,
        title: str,
        triage_verdict: str,
    ) -> PdfReadResult:
        result = self._analyzer(
            query=query,
            url=url,
            title=title,
            triage_verdict=triage_verdict,
        )
        return _coerce_pdf_read_result(result)


def _coerce_pdf_read_result(result: object) -> PdfReadResult:
    if hasattr(result, "relevant"):
        return PdfReadResult(
            relevant=bool(getattr(result, "relevant", False)),
            confidence=float(getattr(result, "confidence", 0.0) or 0.0),
            document_scope=str(getattr(result, "document_scope", "") or ""),
            entity_match_summary=str(getattr(result, "entity_match_summary", "") or ""),
            key_findings=tuple(str(item) for item in (getattr(result, "key_findings", ()) or ())),
            evidence_pages=tuple(int(item) for item in (getattr(result, "evidence_pages", ()) or ())),
        )
    raise TypeError(f"unsupported pdf analyzer result type: {type(result).__name__}")


__all__ = ["RuntimePdfReadGateway"]
