from dataclasses import dataclass


@dataclass(frozen=True)
class PdfAnalysisResult:
    relevant: bool
    confidence: float
    document_scope: str
    entity_match_summary: str
    key_findings: tuple[str, ...] = ()
    evidence_pages: tuple[int, ...] = ()
