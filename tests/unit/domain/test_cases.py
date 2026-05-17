from dataclasses import FrozenInstanceError, is_dataclass

import pytest

from sourcetrace.domain.cases import Case, CaseReport
from sourcetrace.domain.claims import ClaimReportEntry
from sourcetrace.domain.types import HumanReviewStatus, VerificationVerdict


def test_case_is_minimal_frozen_dataclass_with_core_metadata() -> None:
    case = Case(
        case_id="case-1",
        title="Bridge reopening investigation",
        description="Verification workspace for reported bridge reopening claims.",
    )

    assert is_dataclass(case)
    assert case.case_id == "case-1"
    assert case.title == "Bridge reopening investigation"
    assert case.description == (
        "Verification workspace for reported bridge reopening claims."
    )

    with pytest.raises(FrozenInstanceError):
        case.title = "Updated title"


def test_case_supports_minimal_construction_with_empty_links() -> None:
    case = Case(case_id="case-1", title="Bridge reopening investigation")

    assert case.description is None
    assert case.document_ids == ()
    assert case.claim_ids == ()


def test_case_stores_related_document_and_claim_ids_without_object_graphs() -> None:
    case = Case(
        case_id="case-1",
        title="Bridge reopening investigation",
        document_ids=("doc-1", "doc-2"),
        claim_ids=("claim-1", "claim-2"),
    )

    assert case.document_ids == ("doc-1", "doc-2")
    assert case.claim_ids == ("claim-1", "claim-2")


def test_case_is_importable_from_cases_module() -> None:
    import sourcetrace.domain.cases as cases

    assert cases.Case is Case


def test_case_report_is_importable_from_cases_module() -> None:
    import sourcetrace.domain.cases as cases

    assert cases.CaseReport is CaseReport


def test_case_report_stores_case_level_report_entries() -> None:
    entry = ClaimReportEntry(
        claim_id="claim-1",
        case_id="case-1",
        final_verdict=VerificationVerdict.SUPPORT,
        human_review_status=HumanReviewStatus.REVIEWED_ACCEPT,
        summary_text="The bridge reopening claim is supported by reviewed evidence.",
    )
    report = CaseReport(
        case_id="case-1",
        generated_claim_ids=("claim-1", "claim-2"),
        entries=(entry,),
        report_summary="Reviewed claims support the case-level finding.",
    )

    assert is_dataclass(report)
    assert report.case_id == "case-1"
    assert report.generated_claim_ids == ("claim-1", "claim-2")
    assert report.entries == (entry,)
    assert report.report_summary == "Reviewed claims support the case-level finding."


def test_case_report_summary_defaults_to_absent() -> None:
    report = CaseReport(
        case_id="case-1",
        generated_claim_ids=(),
        entries=(),
    )

    assert report.report_summary is None


def test_case_report_is_frozen() -> None:
    report = CaseReport(
        case_id="case-1",
        generated_claim_ids=(),
        entries=(),
    )

    with pytest.raises(FrozenInstanceError):
        report.report_summary = "Cannot mutate frozen case reports."
