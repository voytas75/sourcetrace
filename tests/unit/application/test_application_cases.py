from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from sourcetrace.application import (
    CaseCreationExecution,
    CaseCreationOutcome,
    CaseCreationRequest,
    CaseCreator,
    SourceIngestionExecution,
    SourceIngestionOutcome,
    SourceIngestionRequest,
    SourceIngestor,
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
from sourcetrace.application.interfaces import (
    CaseCreationExecution as InterfacesCaseCreationExecution,
)
from sourcetrace.application.interfaces import CaseCreator as InterfacesCaseCreator
from sourcetrace.application.interfaces import (
    SourceIngestionExecution as InterfacesSourceIngestionExecution,
)
from sourcetrace.application.interfaces import (
    SourceIngestor as InterfacesSourceIngestor,
)
from sourcetrace.domain import Case, Document


def test_application_package_re_exports_case_intake_contracts() -> None:
    assert CaseCreationRequest is ModuleCaseCreationRequest
    assert CaseCreationOutcome is ModuleCaseCreationOutcome
    assert SourceIngestionRequest is ModuleSourceIngestionRequest
    assert SourceIngestionOutcome is ModuleSourceIngestionOutcome
    assert CaseCreator is InterfacesCaseCreator
    assert SourceIngestor is InterfacesSourceIngestor
    assert CaseCreationExecution is InterfacesCaseCreationExecution
    assert SourceIngestionExecution is InterfacesSourceIngestionExecution


def test_case_intake_execution_bundles_keep_explicit_callable_dependencies() -> None:
    def create_case(request: CaseCreationRequest) -> CaseCreationOutcome:
        case = Case(
            case_id=request.case_id,
            title=request.title,
            description=request.description,
        )
        return CaseCreationOutcome(request=request, case=case)

    def ingest_source(request: SourceIngestionRequest) -> SourceIngestionOutcome:
        document = Document(
            document_id=request.document_id,
            case_id=request.case_id,
            source_type=request.source_type,
            source_url=request.source_locator,
            publisher=None,
            author=None,
            title=None,
            published_at=None,
            retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
            content_hash="sha256:test",
            language=None,
        )
        return SourceIngestionOutcome(request=request, document=document)

    execution = CaseCreationExecution(create_case=create_case)
    ingestion = SourceIngestionExecution(ingest_source=ingest_source)

    assert execution.create_case is create_case
    assert ingestion.ingest_source is ingest_source


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
