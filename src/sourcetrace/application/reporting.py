"""Application-layer report assembly contracts."""

from dataclasses import dataclass

from sourcetrace.domain.cases import CaseReport
from sourcetrace.domain.claims import ClaimReportEntry, ClaimReviewDecision


@dataclass(frozen=True)
class ReportAssemblyRequest:
    """Input contract for assembling reviewed claims into report artifacts."""

    case_id: str
    review_decisions: tuple[ClaimReviewDecision, ...]


@dataclass(frozen=True)
class ReportAssemblyOutcome:
    """Output contract for report-ready entries and the case report aggregate."""

    request: ReportAssemblyRequest
    entries: tuple[ClaimReportEntry, ...]
    case_report: CaseReport


__all__ = [
    "ReportAssemblyOutcome",
    "ReportAssemblyRequest",
]
