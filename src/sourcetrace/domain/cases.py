"""Case domain records."""

from dataclasses import dataclass

from sourcetrace.domain.claims import ClaimReportEntry


@dataclass(frozen=True)
class Case:
    """Minimal investigation unit metadata."""

    case_id: str
    title: str
    description: str | None = None
    document_ids: tuple[str, ...] = ()
    claim_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class CaseReport:
    """Case-level report aggregate contract."""

    case_id: str
    generated_claim_ids: tuple[str, ...]
    entries: tuple[ClaimReportEntry, ...]
    report_summary: str | None = None


__all__ = [
    "Case",
    "CaseReport",
]
