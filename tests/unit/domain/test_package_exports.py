from sourcetrace.domain import (
    INFORMATION_CREDIBILITY_FIELD,
    SOURCE_RELIABILITY_FIELD,
    AnalystDisposition,
    Case,
    CaseReport,
    Claim,
    ClaimEvidenceLink,
    ClaimReportEntry,
    ClaimReviewDecision,
    ClaimVerification,
    CredibilityBand,
    Document,
    DocumentChunk,
    DocumentCredibilityAssessment,
    HumanReviewStatus,
    ProvenanceDistance,
    QueueStatus,
    RetrievalHit,
    RetrievalQuery,
    RetrievalResultSet,
    VerificationVerdict,
)
from sourcetrace.domain.cases import Case as CasesCase
from sourcetrace.domain.cases import CaseReport as CasesCaseReport
from sourcetrace.domain.chunks import DocumentChunk as ChunksDocumentChunk
from sourcetrace.domain.claims import Claim as ClaimsClaim
from sourcetrace.domain.claims import ClaimEvidenceLink as ClaimsClaimEvidenceLink
from sourcetrace.domain.claims import ClaimReportEntry as ClaimsClaimReportEntry
from sourcetrace.domain.claims import ClaimReviewDecision as ClaimsClaimReviewDecision
from sourcetrace.domain.claims import ClaimVerification as ClaimsClaimVerification
from sourcetrace.domain.documents import Document as DocumentsDocument
from sourcetrace.domain.documents import (
    DocumentCredibilityAssessment as DocumentsDocumentCredibilityAssessment,
)
from sourcetrace.domain.retrieval import RetrievalHit as RetrievalRetrievalHit
from sourcetrace.domain.retrieval import RetrievalQuery as RetrievalRetrievalQuery
from sourcetrace.domain.retrieval import RetrievalResultSet as RetrievalRetrievalResultSet
from sourcetrace.domain.types import (
    INFORMATION_CREDIBILITY_FIELD as TYPES_INFORMATION_CREDIBILITY_FIELD,
)
from sourcetrace.domain.types import SOURCE_RELIABILITY_FIELD as TYPES_SOURCE_RELIABILITY_FIELD
from sourcetrace.domain.types import AnalystDisposition as TypesAnalystDisposition
from sourcetrace.domain.types import CredibilityBand as TypesCredibilityBand
from sourcetrace.domain.types import HumanReviewStatus as TypesHumanReviewStatus
from sourcetrace.domain.types import ProvenanceDistance as TypesProvenanceDistance
from sourcetrace.domain.types import QueueStatus as TypesQueueStatus
from sourcetrace.domain.types import VerificationVerdict as TypesVerificationVerdict


def test_package_re_exports_domain_records() -> None:
    assert Case is CasesCase
    assert CaseReport is CasesCaseReport
    assert Claim is ClaimsClaim
    assert ClaimEvidenceLink is ClaimsClaimEvidenceLink
    assert ClaimReportEntry is ClaimsClaimReportEntry
    assert ClaimReviewDecision is ClaimsClaimReviewDecision
    assert ClaimVerification is ClaimsClaimVerification
    assert Document is DocumentsDocument
    assert DocumentChunk is ChunksDocumentChunk
    assert DocumentCredibilityAssessment is DocumentsDocumentCredibilityAssessment
    assert RetrievalHit is RetrievalRetrievalHit
    assert RetrievalQuery is RetrievalRetrievalQuery
    assert RetrievalResultSet is RetrievalRetrievalResultSet


def test_package_re_exports_domain_enums() -> None:
    assert VerificationVerdict is TypesVerificationVerdict
    assert HumanReviewStatus is TypesHumanReviewStatus
    assert AnalystDisposition is TypesAnalystDisposition
    assert QueueStatus is TypesQueueStatus
    assert CredibilityBand is TypesCredibilityBand
    assert ProvenanceDistance is TypesProvenanceDistance


def test_package_re_exports_osint_field_names() -> None:
    assert SOURCE_RELIABILITY_FIELD == TYPES_SOURCE_RELIABILITY_FIELD
    assert INFORMATION_CREDIBILITY_FIELD == TYPES_INFORMATION_CREDIBILITY_FIELD
