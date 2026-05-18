from sourcetrace.application import (
    CaseCreationExecution,
    CaseCreator,
    ClaimExtractionExecution,
    ClaimExtractor,
    ClaimReviewExecution,
    ClaimReviewer,
    ClaimVerificationExecution,
    ClaimVerifier,
    CredibilityAssessmentExecution,
    CredibilityAssessor,
    DocumentPreparationExecution,
    DocumentPreparer,
    ReportAssembler,
    ReportAssemblyExecution,
    SourceIngestionExecution,
    SourceIngestor,
)
from sourcetrace.application.interfaces import (
    CaseCreationExecution as InterfacesCaseCreationExecution,
)
from sourcetrace.application.interfaces import (
    CaseCreator as InterfacesCaseCreator,
)
from sourcetrace.application.interfaces import (
    ClaimExtractionExecution as InterfacesClaimExtractionExecution,
)
from sourcetrace.application.interfaces import (
    ClaimExtractor as InterfacesClaimExtractor,
)
from sourcetrace.application.interfaces import (
    ClaimReviewExecution as InterfacesClaimReviewExecution,
)
from sourcetrace.application.interfaces import (
    ClaimReviewer as InterfacesClaimReviewer,
)
from sourcetrace.application.interfaces import (
    ClaimVerificationExecution as InterfacesClaimVerificationExecution,
)
from sourcetrace.application.interfaces import (
    ClaimVerifier as InterfacesClaimVerifier,
)
from sourcetrace.application.interfaces import (
    CredibilityAssessmentExecution as InterfacesCredibilityAssessmentExecution,
)
from sourcetrace.application.interfaces import (
    CredibilityAssessor as InterfacesCredibilityAssessor,
)
from sourcetrace.application.interfaces import (
    DocumentPreparationExecution as InterfacesDocumentPreparationExecution,
)
from sourcetrace.application.interfaces import (
    DocumentPreparer as InterfacesDocumentPreparer,
)
from sourcetrace.application.interfaces import (
    ReportAssembler as InterfacesReportAssembler,
)
from sourcetrace.application.interfaces import (
    ReportAssemblyExecution as InterfacesReportAssemblyExecution,
)
from sourcetrace.application.interfaces import (
    SourceIngestionExecution as InterfacesSourceIngestionExecution,
)
from sourcetrace.application.interfaces import (
    SourceIngestor as InterfacesSourceIngestor,
)


def test_application_package_re_exports_execution_seams() -> None:
    assert CaseCreationExecution is InterfacesCaseCreationExecution
    assert CaseCreator is InterfacesCaseCreator
    assert SourceIngestionExecution is InterfacesSourceIngestionExecution
    assert SourceIngestor is InterfacesSourceIngestor
    assert DocumentPreparationExecution is InterfacesDocumentPreparationExecution
    assert DocumentPreparer is InterfacesDocumentPreparer
    assert ClaimExtractionExecution is InterfacesClaimExtractionExecution
    assert ClaimExtractor is InterfacesClaimExtractor
    assert ClaimVerificationExecution is InterfacesClaimVerificationExecution
    assert ClaimVerifier is InterfacesClaimVerifier
    assert ClaimReviewExecution is InterfacesClaimReviewExecution
    assert ClaimReviewer is InterfacesClaimReviewer
    assert ReportAssemblyExecution is InterfacesReportAssemblyExecution
    assert ReportAssembler is InterfacesReportAssembler
    assert CredibilityAssessmentExecution is InterfacesCredibilityAssessmentExecution
    assert CredibilityAssessor is InterfacesCredibilityAssessor


def test_application_execution_container_shapes_are_frozen_dataclasses() -> None:
    assert getattr(CaseCreationExecution, "__dataclass_fields__", None) is not None
    assert getattr(SourceIngestionExecution, "__dataclass_fields__", None) is not None
    assert getattr(DocumentPreparationExecution, "__dataclass_fields__", None) is not None
    assert getattr(ClaimExtractionExecution, "__dataclass_fields__", None) is not None
    assert getattr(ClaimVerificationExecution, "__dataclass_fields__", None) is not None
    assert getattr(ClaimReviewExecution, "__dataclass_fields__", None) is not None
    assert getattr(ReportAssemblyExecution, "__dataclass_fields__", None) is not None
    assert getattr(CredibilityAssessmentExecution, "__dataclass_fields__", None) is not None
    assert tuple(ClaimExtractionExecution.__dataclass_fields__) == ("extract_claims",)
    assert tuple(ClaimVerificationExecution.__dataclass_fields__) == ("verify_claim",)
    assert tuple(ClaimReviewExecution.__dataclass_fields__) == ("review_claim",)
    assert tuple(ReportAssemblyExecution.__dataclass_fields__) == ("assemble_report",)
    assert tuple(CredibilityAssessmentExecution.__dataclass_fields__) == ("assess_credibility",)


def test_application_execution_seams_are_protocol_types() -> None:
    assert getattr(CaseCreator, "_is_protocol", False) is True
    assert getattr(SourceIngestor, "_is_protocol", False) is True
    assert getattr(DocumentPreparer, "_is_protocol", False) is True
    assert getattr(ClaimExtractor, "_is_protocol", False) is True
    assert getattr(ClaimVerifier, "_is_protocol", False) is True
    assert getattr(ClaimReviewer, "_is_protocol", False) is True
    assert getattr(ReportAssembler, "_is_protocol", False) is True
    assert getattr(CredibilityAssessor, "_is_protocol", False) is True


def test_application_execution_seams_define_callable_entrypoint() -> None:
    assert callable(CaseCreator.__call__)
    assert callable(SourceIngestor.__call__)
    assert callable(DocumentPreparer.__call__)
    assert callable(ClaimExtractor.__call__)
    assert callable(ClaimVerifier.__call__)
    assert callable(ClaimReviewer.__call__)
    assert callable(ReportAssembler.__call__)
    assert callable(CredibilityAssessor.__call__)
