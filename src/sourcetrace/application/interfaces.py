"""Execution-side application interfaces for use-case orchestration."""

from dataclasses import dataclass
from typing import Protocol

from sourcetrace.domain.documents import Document
from sourcetrace.domain.chunks import DocumentChunk

from sourcetrace.application.cases import (
    CaseCreationOutcome,
    CaseCreationRequest,
    SourceIngestionOutcome,
    SourceIngestionRequest,
)
from sourcetrace.application.credibility import (
    CredibilityAssessmentOutcome,
    CredibilityAssessmentRequest,
)
from sourcetrace.application.documents import (
    DocumentPreparationOutcome,
    DocumentPreparationRequest,
)
from sourcetrace.application.extraction import (
    ClaimExtractionOutcome,
    ClaimExtractionRequest,
)
from sourcetrace.application.reporting import (
    ReportAssemblyOutcome,
    ReportAssemblyRequest,
)
from sourcetrace.application.review import ClaimReviewOutcome, ClaimReviewRequest
from sourcetrace.application.verification import (
    ClaimVerificationOutcome,
    ClaimVerificationRequest,
)


class CaseCreator(Protocol):
    """Execution seam for opening a new investigation case."""

    def __call__(self, request: CaseCreationRequest) -> CaseCreationOutcome:
        ...


@dataclass(frozen=True)
class CaseCreationExecution:
    """Case intake seam bundle for explicit request/outcome callable wiring."""

    create_case: CaseCreator


class SourceIngestor(Protocol):
    """Execution seam for attaching a source artifact to an existing case."""

    def __call__(self, request: SourceIngestionRequest) -> SourceIngestionOutcome:
        ...


@dataclass(frozen=True)
class SourceIngestionExecution:
    """Source intake seam bundle for explicit request/outcome callable wiring."""

    ingest_source: SourceIngestor


class DocumentPreparer(Protocol):
    """Execution seam for preparing an ingested document for downstream analysis."""

    def __call__(self, request: DocumentPreparationRequest) -> DocumentPreparationOutcome:
        ...


@dataclass(frozen=True)
class DocumentPreparationExecution:
    """Document preparation seam bundle for explicit request/outcome callable wiring."""

    prepare_document: DocumentPreparer


class ClaimExtractor(Protocol):
    """Execution seam for extracting structured claims from prepared evidence."""

    def __call__(self, request: ClaimExtractionRequest) -> ClaimExtractionOutcome:
        ...


@dataclass(frozen=True)
class ClaimExtractionExecution:
    """Claim extraction seam bundle for explicit request/outcome callable wiring."""

    extract_claims: ClaimExtractor


class ClaimExtractionRuntimeExtractor(Protocol):
    """Execution seam for extracting claims from prepared document context via runtime dependencies."""

    def __call__(
        self,
        request: ClaimExtractionRequest,
        *,
        document: Document,
        chunks: tuple[DocumentChunk, ...],
    ) -> ClaimExtractionOutcome:
        ...


@dataclass(frozen=True)
class ClaimExtractionRuntime:
    """Runtime seam bundle for extraction paths needing prepared document context."""

    extract_claims: ClaimExtractionRuntimeExtractor


class ClaimVerifier(Protocol):
    """Execution seam for verifying one extracted claim against retrieved evidence."""

    def __call__(self, request: ClaimVerificationRequest) -> ClaimVerificationOutcome:
        ...


@dataclass(frozen=True)
class ClaimVerificationExecution:
    """Claim verification seam bundle for explicit request/outcome callable wiring."""

    verify_claim: ClaimVerifier


class ClaimReviewer(Protocol):
    """Execution seam for analyst review of a verified claim."""

    def __call__(self, request: ClaimReviewRequest) -> ClaimReviewOutcome:
        ...


@dataclass(frozen=True)
class ClaimReviewExecution:
    """Claim review seam bundle for explicit request/outcome callable wiring."""

    review_claim: ClaimReviewer


class ReportAssembler(Protocol):
    """Execution seam for assembling reviewed claims into report artifacts."""

    def __call__(self, request: ReportAssemblyRequest) -> ReportAssemblyOutcome:
        ...


@dataclass(frozen=True)
class ReportAssemblyExecution:
    """Report assembly seam bundle for explicit request/outcome callable wiring."""

    assemble_report: ReportAssembler


class CredibilityAssessor(Protocol):
    """Execution seam for advisory document credibility assessment."""

    def __call__(
        self,
        request: CredibilityAssessmentRequest,
    ) -> CredibilityAssessmentOutcome:
        ...


@dataclass(frozen=True)
class CredibilityAssessmentExecution:
    """Credibility assessment seam bundle for explicit request/outcome callable wiring."""

    assess_credibility: CredibilityAssessor


__all__ = [
    "CaseCreationExecution",
    "CaseCreator",
    "ClaimExtractionExecution",
    "ClaimExtractionRuntime",
    "ClaimExtractionRuntimeExtractor",
    "ClaimExtractor",
    "ClaimReviewExecution",
    "ClaimReviewer",
    "ClaimVerificationExecution",
    "ClaimVerifier",
    "CredibilityAssessmentExecution",
    "CredibilityAssessor",
    "DocumentPreparationExecution",
    "DocumentPreparer",
    "ReportAssembler",
    "ReportAssemblyExecution",
    "SourceIngestionExecution",
    "SourceIngestor",
]
