from dataclasses import FrozenInstanceError

import pytest

from sourcetrace.storage import (
    CaseRepository,
    ClaimRepository,
    CorePersistence,
    DocumentRepository,
)
from sourcetrace.storage.interfaces import CaseRepository as InterfacesCaseRepository
from sourcetrace.storage.interfaces import ClaimRepository as InterfacesClaimRepository
from sourcetrace.storage.interfaces import CorePersistence as InterfacesCorePersistence
from sourcetrace.storage.interfaces import DocumentRepository as InterfacesDocumentRepository


def test_storage_package_re_exports_persistence_seams() -> None:
    assert CaseRepository is InterfacesCaseRepository
    assert DocumentRepository is InterfacesDocumentRepository
    assert ClaimRepository is InterfacesClaimRepository
    assert CorePersistence is InterfacesCorePersistence


def test_persistence_repositories_are_protocol_types() -> None:
    assert getattr(CaseRepository, "_is_protocol", False) is True
    assert getattr(DocumentRepository, "_is_protocol", False) is True
    assert getattr(ClaimRepository, "_is_protocol", False) is True


def test_persistence_repositories_define_minimal_core_methods() -> None:
    assert callable(CaseRepository.save_case)
    assert callable(CaseRepository.get_case)
    assert callable(DocumentRepository.save_document)
    assert callable(DocumentRepository.get_document)
    assert callable(DocumentRepository.save_chunks)
    assert callable(DocumentRepository.list_chunks_for_document)
    assert callable(ClaimRepository.save_claims)
    assert callable(ClaimRepository.get_claim)
    assert callable(ClaimRepository.list_claims_for_case)
    assert callable(ClaimRepository.save_evidence_links)
    assert callable(ClaimRepository.save_verification)
    assert callable(ClaimRepository.save_review_decision)


def test_core_persistence_container_shape_is_frozen_dataclass() -> None:
    assert getattr(CorePersistence, "__dataclass_fields__", None) is not None
    assert tuple(CorePersistence.__dataclass_fields__) == (
        "cases",
        "documents",
        "claims",
    )

    cases = object()
    documents = object()
    claims = object()
    persistence = CorePersistence(cases=cases, documents=documents, claims=claims)

    assert persistence.cases is cases
    assert persistence.documents is documents
    assert persistence.claims is claims

    with pytest.raises(FrozenInstanceError):
        setattr(persistence, "cases", object())


def test_report_and_run_metadata_persistence_are_not_frozen_in_7x() -> None:
    import sourcetrace.storage.interfaces as interfaces

    assert "ReportRepository" not in interfaces.__all__
    assert "RunMetadataStore" not in interfaces.__all__
