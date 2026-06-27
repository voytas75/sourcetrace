from __future__ import annotations

from enum import StrEnum


class FeatureId(StrEnum):
    DEEP_RESEARCH = "deep_research"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class StageId(StrEnum):
    PLANNING = "planning"
    QUERY_REFINEMENT = "query_refinement"
    EVIDENCE_JUDGE = "evidence_judge"
    SYNTHESIS = "synthesis"


class StageStatus(StrEnum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    DEGRADED = "degraded"


class ReceiptCoverageStatus(StrEnum):
    TRACKED = "tracked"
    PROVIDER_MISSING_USAGE = "provider_missing_usage"
    ESTIMATED = "estimated"
    NON_LLM_BACKEND = "non_llm_backend"


class DegradationReason(StrEnum):
    FALLBACK_USED = "fallback_used"
    PROVIDER_ERROR = "provider_error"
    TIMEOUT = "timeout"
    VALIDATION_FALLBACK = "validation_fallback"
    UNKNOWN = "unknown"
