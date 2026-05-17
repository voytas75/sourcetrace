"""Application report assembly contract tests."""

from dataclasses import FrozenInstanceError

import pytest

from sourcetrace.application import ReportAssemblyOutcome, ReportAssemblyRequest
from sourcetrace.application.reporting import ReportAssemblyOutcome as ModuleReportAssemblyOutcome
from sourcetrace.application.reporting import ReportAssemblyRequest as ModuleReportAssemblyRequest
from sourcetrace.domain import CaseReport, ClaimReportEntry, ClaimReviewDecision
from sourcetrace.domain.types import AnalystDisposition, HumanReviewStatus, VerificationVerdict


def test_application_package_re_exports_report_assembly_contracts() -> None:
    assert ReportAssemblyRequest is ModuleReportAssemblyRequest
    assert ReportAssemblyOutcome is ModuleReportAssemblyOutcome


def test_report_assembly_request_and_outcome_keep_review_entries_and_case_report() -> None:
    review_decisions = (
        ClaimReviewDecision(
            claim_id="claim-1",
            case_id="case-1",
            human_review_status=HumanReviewStatus.REVIEWED_ACCEPT,
            analyst_disposition=AnalystDisposition.CONFIRMED_SUPPORT,
            final_verdict=VerificationVerdict.SUPPORT,
            review_notes="Analyst confirmed support",
        ),
    )
    entries = (
        ClaimReportEntry(
            claim_id="claim-1",
            case_id="case-1",
            final_verdict=VerificationVerdict.SUPPORT,
            human_review_status=HumanReviewStatus.REVIEWED_ACCEPT,
            summary_text="Claim supported by reviewed evidence.",
            supporting_chunk_ids=("chunk-1",),
            contradicting_chunk_ids=(),
        ),
    )
    case_report = CaseReport(
        case_id="case-1",
        generated_claim_ids=("claim-1",),
        entries=entries,
        report_summary="One reviewed claim ready for reporting.",
    )

    request = ReportAssemblyRequest(
        case_id="case-1",
        review_decisions=review_decisions,
    )
    outcome = ReportAssemblyOutcome(
        request=request,
        entries=entries,
        case_report=case_report,
    )

    assert outcome.request is request
    assert outcome.entries == entries
    assert outcome.case_report is case_report


def test_report_assembly_contracts_are_immutable() -> None:
    request = ReportAssemblyRequest(
        case_id="case-1",
        review_decisions=(),
    )

    with pytest.raises(FrozenInstanceError):
        setattr(request, "case_id", "case-2")
