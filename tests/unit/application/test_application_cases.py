"""Application case intake contract tests."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from sourcetrace.application import (
    CaseCreationOutcome,
    CaseCreationRequest,
    SourceIngestionOutcome,
    SourceIngestionRequest,
)
from sourcetrace.application.cases import (
    CaseCreationOutcome as ModuleCaseCreationOutcome,
)
from sourcetrace.application.cases import (
    CaseCreationRequest as ModuleCaseCreationRequest,
)
from sourcetrace.application.cases import (
    SourceIngestionOutcome as ModuleSourceIngestionOutcome,
)
from sourcetrace.application.cases import (
    SourceIngestionRequest as ModuleSourceIngestionRequest,
)
from sourcetrace.domain import Case, Document


def test_application_package_re_exports_case_intake_contracts() -> None:
    assert CaseCreationRequest is ModuleCaseCreationRequest
    assert CaseCreationOutcome is ModuleCaseCreationOutcome
    assert SourceIngestionRequest is ModuleSourceIngestionRequest
    assert SourceIngestionOutcome is ModuleSourceIngestionOutcome


def test_case_creation_request_and_outcome_keep_case_context() -> None:
    request = CaseCreationRequest(
        case_id="case-1",
        title="Investigate network narrative",
        description="Track claims and evidence",
    )
    case = Case(
        case_id="case-1",
        title="Investigate network narrative",
        description="Track claims and evidence",
        document_ids=(),
        claim_ids=(),
    )

    outcome = CaseCreationOutcome(request=request, case=case)

    assert outcome.request is request
    assert outcome.case is case
    assert outcome.case.case_id == "case-1"


def test_source_ingestion_request_and_outcome_keep_document_context() -> None:
    request = SourceIngestionRequest(
        case_id="case-1",
        document_id="doc-1",
        source_type="url",
        source_locator="https://example.test/report",
    )
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

    outcome = SourceIngestionOutcome(request=request, document=document)

    assert outcome.request is request
    assert outcome.document is document
    assert outcome.document.document_id == "doc-1"


def test_case_intake_contracts_are_immutable() -> None:
    request = CaseCreationRequest(
        case_id="case-1",
        title="Investigate network narrative",
    )

    with pytest.raises(FrozenInstanceError):
        setattr(request, "title", "Mutated title")
