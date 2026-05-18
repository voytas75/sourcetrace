from sourcetrace.application import (
    CaseCreationOutcome,
    CaseCreationRequest,
    ClaimExtractionOutcome,
    ClaimExtractionRequest,
    build_llm_claim_extractor,
    build_llm_credibility_assessor,
    ClaimReviewOutcome,
    ClaimReviewRequest,
    ClaimVerificationOutcome,
    ClaimVerificationRequest,
    CredibilityAssessmentOutcome,
    CredibilityAssessmentRequest,
    DocumentPreparationOutcome,
    DocumentPreparationRequest,
    ReportAssemblyOutcome,
    ReportAssemblyRequest,
    SourceIngestionOutcome,
    SourceIngestionRequest,
)
from sourcetrace.application.cases import (
    CaseCreationOutcome as CasesCaseCreationOutcome,
)
from sourcetrace.application.cases import (
    CaseCreationRequest as CasesCaseCreationRequest,
)
from sourcetrace.application.cases import (
    SourceIngestionOutcome as CasesSourceIngestionOutcome,
)
from sourcetrace.application.cases import (
    SourceIngestionRequest as CasesSourceIngestionRequest,
)
from sourcetrace.application.credibility import (
    CredibilityAssessmentOutcome as CredibilityCredibilityAssessmentOutcome,
)
from sourcetrace.application.credibility import (
    CredibilityAssessmentRequest as CredibilityCredibilityAssessmentRequest,
)
from sourcetrace.application.credibility_runtime import (
    build_llm_credibility_assessor as RuntimeBuildLlmCredibilityAssessor,
)
from sourcetrace.application.documents import (
    DocumentPreparationOutcome as DocumentsDocumentPreparationOutcome,
)
from sourcetrace.application.documents import (
    DocumentPreparationRequest as DocumentsDocumentPreparationRequest,
)
from sourcetrace.application.extraction import (
    ClaimExtractionOutcome as ExtractionClaimExtractionOutcome,
)
from sourcetrace.application.extraction import (
    ClaimExtractionRequest as ExtractionClaimExtractionRequest,
)
from sourcetrace.application.extraction_runtime import build_llm_claim_extractor as RuntimeBuildLlmClaimExtractor
from sourcetrace.application.reporting import (
    ReportAssemblyOutcome as ReportingReportAssemblyOutcome,
)
from sourcetrace.application.reporting import (
    ReportAssemblyRequest as ReportingReportAssemblyRequest,
)
from sourcetrace.application.review import ClaimReviewOutcome as ReviewClaimReviewOutcome
from sourcetrace.application.review import ClaimReviewRequest as ReviewClaimReviewRequest
from sourcetrace.application.verification import (
    ClaimVerificationOutcome as VerificationClaimVerificationOutcome,
)
from sourcetrace.application.verification import (
    ClaimVerificationRequest as VerificationClaimVerificationRequest,
)


def test_application_package_re_exports_verification_contracts() -> None:
    assert ClaimVerificationRequest is VerificationClaimVerificationRequest
    assert ClaimVerificationOutcome is VerificationClaimVerificationOutcome


def test_application_package_re_exports_case_intake_contracts() -> None:
    assert CaseCreationRequest is CasesCaseCreationRequest
    assert CaseCreationOutcome is CasesCaseCreationOutcome
    assert SourceIngestionRequest is CasesSourceIngestionRequest
    assert SourceIngestionOutcome is CasesSourceIngestionOutcome


def test_application_package_re_exports_document_preparation_contracts() -> None:
    assert DocumentPreparationRequest is DocumentsDocumentPreparationRequest
    assert DocumentPreparationOutcome is DocumentsDocumentPreparationOutcome


def test_application_package_re_exports_claim_extraction_contracts() -> None:
    assert ClaimExtractionRequest is ExtractionClaimExtractionRequest
    assert ClaimExtractionOutcome is ExtractionClaimExtractionOutcome
    assert build_llm_claim_extractor is RuntimeBuildLlmClaimExtractor


def test_application_package_re_exports_human_review_contracts() -> None:
    assert ClaimReviewRequest is ReviewClaimReviewRequest
    assert ClaimReviewOutcome is ReviewClaimReviewOutcome


def test_application_package_re_exports_report_assembly_contracts() -> None:
    assert ReportAssemblyRequest is ReportingReportAssemblyRequest
    assert ReportAssemblyOutcome is ReportingReportAssemblyOutcome


def test_application_package_re_exports_credibility_assessment_contracts() -> None:
    assert CredibilityAssessmentRequest is CredibilityCredibilityAssessmentRequest
    assert CredibilityAssessmentOutcome is CredibilityCredibilityAssessmentOutcome
    assert build_llm_credibility_assessor is RuntimeBuildLlmCredibilityAssessor
