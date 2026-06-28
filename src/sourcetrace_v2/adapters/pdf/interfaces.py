from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PdfReadResult:
    relevant: bool
    confidence: float
    document_scope: str
    entity_match_summary: str
    key_findings: tuple[str, ...] = ()
    evidence_pages: tuple[int, ...] = ()


class PdfReadGateway(Protocol):
    """Optional v2 execution seam for reading a PDF artifact into typed evidence."""

    def read(
        self,
        *,
        query: str,
        url: str,
        title: str,
        triage_verdict: str,
    ) -> PdfReadResult:
        ...
