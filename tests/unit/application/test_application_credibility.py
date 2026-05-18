"""Application credibility assessment contract tests."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from sourcetrace.application import (
    CredibilityAssessmentExecution,
    CredibilityAssessmentOutcome,
    CredibilityAssessmentRequest,
    CredibilityAssessor,
)
from sourcetrace.application.credibility import (
    CredibilityAssessmentOutcome as ModuleCredibilityAssessmentOutcome,
)
from sourcetrace.application.credibility import (
    CredibilityAssessmentRequest as ModuleCredibilityAssessmentRequest,
)
from sourcetrace.application.interfaces import (
    CredibilityAssessmentExecution as InterfacesCredibilityAssessmentExecution,
)
from sourcetrace.application.interfaces import (
    CredibilityAssessor as InterfacesCredibilityAssessor,
)
from sourcetrace.domain import Document, DocumentCredibilityAssessment
from sourcetrace.domain.types import CredibilityBand, ProvenanceDistance


def test_application_package_re_exports_credibility_assessment_contracts() -> None:
    assert CredibilityAssessmentRequest is ModuleCredibilityAssessmentRequest
    assert CredibilityAssessmentOutcome is ModuleCredibilityAssessmentOutcome
    assert CredibilityAssessor is InterfacesCredibilityAssessor
    assert CredibilityAssessmentExecution is InterfacesCredibilityAssessmentExecution


def test_credibility_assessment_execution_bundle_keeps_explicit_callable_dependency() -> None:
    def assess_credibility(
        request: CredibilityAssessmentRequest,
    ) -> CredibilityAssessmentOutcome:
        assessment = DocumentCredibilityAssessment(
            assessment_id="cred-1",
            document_id=request.document.document_id,
            source_reliability=CredibilityBand.HIGH,
            information_credibility=CredibilityBand.MEDIUM,
            source_reliability_factors=("publisher_history",),
            information_credibility_factors=("partial_corroboration",),
            provenance_distance=ProvenanceDistance.PRIMARY,
            method=request.assessment_method or "rule_based_v1",
            notes="Needs analyst review before reporting.",
            assessed_by="system",
            assessed_at=datetime(2026, 5, 18, 0, 10, tzinfo=UTC),
            override=False,
        )
        return CredibilityAssessmentOutcome(request=request, assessment=assessment)

    execution = CredibilityAssessmentExecution(assess_credibility=assess_credibility)

    assert execution.assess_credibility is assess_credibility


def test_credibility_assessment_request_and_outcome_keep_document_and_assessment() -> None:
    document = Document(
        document_id="doc-1",
        case_id="case-1",
        source_type="url",
        source_url="https://example.test/report",
        publisher="Example News",
        author="Analyst",
        title="Network report",
        published_at=datetime(2026, 5, 18, 0, 0, tzinfo=UTC),
        retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
        content_hash="sha256:abc123",
        language="en",
    )
    assessment = DocumentCredibilityAssessment(
        assessment_id="cred-1",
        document_id="doc-1",
        source_reliability=CredibilityBand.HIGH,
        information_credibility=CredibilityBand.MEDIUM,
        source_reliability_factors=("publisher_history",),
        information_credibility_factors=("partial_corroboration",),
        provenance_distance=ProvenanceDistance.PRIMARY,
        method="rule_based_v1",
        notes="Needs analyst review before reporting.",
        assessed_by="system",
        assessed_at=datetime(2026, 5, 18, 0, 10, tzinfo=UTC),
        override=False,
    )

    request = CredibilityAssessmentRequest(
        document=document,
        assessment_method="rule_based_v1",
    )
    outcome = CredibilityAssessmentOutcome(
        request=request,
        assessment=assessment,
    )

    assert outcome.request is request
    assert outcome.request.document is document
    assert outcome.assessment is assessment


def test_credibility_assessment_contracts_are_immutable() -> None:
    request = CredibilityAssessmentRequest(
        document=Document(
            document_id="doc-1",
            case_id="case-1",
            source_type="url",
            source_url="https://example.test/report",
            publisher=None,
            author=None,
            title=None,
            published_at=None,
            retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
            content_hash="sha256:abc123",
            language="en",
        )
    )

    with pytest.raises(FrozenInstanceError):
        setattr(request, "assessment_method", "other")
