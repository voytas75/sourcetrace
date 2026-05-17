"""Canonical domain status and verdict types."""

from enum import Enum


class VerificationVerdict(str, Enum):
    """System-generated claim verification verdict."""

    SUPPORT = "support"
    CONTRADICT = "contradict"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class HumanReviewStatus(str, Enum):
    """Lifecycle state for human review of a claim."""

    UNREVIEWED = "unreviewed"
    REVIEWED_ACCEPT = "reviewed_accept"
    REVIEWED_OVERRIDE = "reviewed_override"
    NEEDS_FOLLOWUP = "needs_followup"
    EXCLUDED = "excluded"
    ESCALATED = "escalated"


class AnalystDisposition(str, Enum):
    """Final analyst disposition for report eligibility decisions."""

    CONFIRMED_SUPPORT = "confirmed_support"
    CONFIRMED_CONTRADICTION = "confirmed_contradiction"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NEEDS_MORE_COLLECTION = "needs_more_collection"
    EXCLUDE_FROM_REPORT = "exclude_from_report"


class QueueStatus(str, Enum):
    """Workflow status for analyst review queue items."""

    NEW = "new"
    TRIAGED = "triaged"
    IN_REVIEW = "in_review"
    ON_HOLD = "on_hold"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class CredibilityBand(str, Enum):
    """Advisory OSINT-style credibility band."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class ProvenanceDistance(str, Enum):
    """Distance from original source material."""

    PRIMARY = "primary"
    NEAR_PRIMARY = "near_primary"
    SECONDARY = "secondary"
    UNKNOWN = "unknown"


SOURCE_RELIABILITY_FIELD = "source_reliability"
INFORMATION_CREDIBILITY_FIELD = "information_credibility"


__all__ = [
    "AnalystDisposition",
    "CredibilityBand",
    "HumanReviewStatus",
    "INFORMATION_CREDIBILITY_FIELD",
    "ProvenanceDistance",
    "QueueStatus",
    "SOURCE_RELIABILITY_FIELD",
    "VerificationVerdict",
]
