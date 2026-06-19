"""Core domain objects and contracts."""

from sourcetrace.domain.cases import Case, CaseReport
from sourcetrace.domain.chunks import DocumentChunk
from sourcetrace.domain.claims import (
    Claim,
    ClaimEvidenceLink,
    ClaimReportEntry,
    ClaimReviewDecision,
    ClaimVerification,
)
from sourcetrace.domain.documents import Document, DocumentCredibilityAssessment
from sourcetrace.domain.research import (
    ResearchCompletionMode,
    ResearchFinding,
    ResearchJob,
    ResearchJobStatus,
    ResearchPhase,
    ResearchProgressEvent,
    ResearchResultArtifact,
    ResearchSettings,
    ResearchSource,
    ResearchStats,
)
from sourcetrace.domain.retrieval import RetrievalHit, RetrievalQuery, RetrievalResultSet
from sourcetrace.domain.types import (
    INFORMATION_CREDIBILITY_FIELD,
    SOURCE_RELIABILITY_FIELD,
    AnalystDisposition,
    CredibilityBand,
    HumanReviewStatus,
    ProvenanceDistance,
    QueueStatus,
    VerificationVerdict,
)

__all__ = [
    "AnalystDisposition",
    "Case",
    "CaseReport",
    "Claim",
    "ClaimEvidenceLink",
    "ClaimReportEntry",
    "ClaimReviewDecision",
    "ClaimVerification",
    "CredibilityBand",
    "Document",
    "DocumentChunk",
    "DocumentCredibilityAssessment",
    "HumanReviewStatus",
    "INFORMATION_CREDIBILITY_FIELD",
    "ProvenanceDistance",
    "QueueStatus",
    "ResearchCompletionMode",
    "ResearchFinding",
    "ResearchJob",
    "ResearchJobStatus",
    "ResearchPhase",
    "ResearchProgressEvent",
    "ResearchResultArtifact",
    "ResearchSettings",
    "ResearchSource",
    "ResearchStats",
    "RetrievalHit",
    "RetrievalQuery",
    "RetrievalResultSet",
    "SOURCE_RELIABILITY_FIELD",
    "VerificationVerdict",
]
