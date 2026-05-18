"""Application report assembly contract tests."""

from dataclasses import FrozenInstanceError

import pytest

from sourcetrace.application import (
    ReportAssemblyExecution,
    ReportAssemblyOutcome,
    ReportAssemblyRequest,
    ReportAssembler,
)
from sourcetrace.application.reporting import ReportAssemblyOutcome as ModuleReportAssemblyOutcome
from sourcetrace.application.reporting import ReportAssemblyRequest as ModuleReportAssemblyRequest
from sourcetrace.application.interfaces import (
    ReportAssemblyExecution as InterfacesReportAssemblyExecution,
)
from sourcetrace.application.interfaces import (
    ReportAssembler as InterfacesReportAssembler,
)
from sourcetrace.domain import CaseReport, ClaimReportEntry, ClaimReviewDecision
from sourcetrace.domain.types import AnalystDisposition, HumanReviewStatus, VerificationVerdict


def test_application_package_re_exports_report_assembly_contracts() -> None:
    assert ReportAssemblyRequest is ModuleReportAssemblyRequest
    assert ReportAssemblyOutcome is ModuleReportAssemblyOutcome
    assert ReportAssembler is InterfacesReportAssembler
    assert ReportAssemblyExecution is InterfacesReportAssemblyExecution


def test_report_assembly_execution_bundle_keeps_explicit_callable_dependency() -> None:
    def assemble_report(request: ReportAssemblyRequest) -> ReportAssemblyOutcome:
        entries = tuple(
            ClaimReportEntry(
                claim_id=decision.claim_id,
                case_id=decision.case_id,
                final_verdict=decision.final_verdict or VerificationVerdict.INSUFFICIENT_EVIDENCE,
                human_review_status=decision.human_review_status,
                summary_text=decision.review_notes or "Reviewed claim ready for reporting.",
                supporting_chunk_ids=(),
                contradicting_chunk_ids=(),
            )
            for decision in request.review_decisions
        )
        case_report = CaseReport(
            case_id=request.case_id,
            generated_claim_ids=tuple(entry.claim_id for entry in entries),
            entries=entries,
            report_summary=f"{len(entries)} reviewed claims ready for reporting.",
        )
        return ReportAssemblyOutcome(
            request=request,
            entries=entries,
            case_report=case_report,
        )

    execution = ReportAssemblyExecution(assemble_report=assemble_report)

    assert execution.assemble_report is assemble_report


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
