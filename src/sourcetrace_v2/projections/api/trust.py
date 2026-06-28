from __future__ import annotations

from sourcetrace_v2.core.contracts.read_models import PersistedExecutionView, PersistedViewStatus

_LOW_BANDS = {"none", "low"}
_STRONG_BANDS = {"high", "medium"}


TRUST_USABLE = "usable"
TRUST_WEAK = "weak"
TRUST_NEEDS_REVIEW = "needs_review"
TRUST_DEGRADED = "degraded"


def project_operator_trust(*, view: PersistedExecutionView) -> dict[str, object]:
    artifact = view.artifact
    compiled = view.compiled_artifact
    selected_count = len(compiled.selected_evidence) if compiled is not None else 0
    candidate_count = len(artifact.evidence_candidates) if artifact is not None else 0

    reasons: list[str] = []

    if view.status is not PersistedViewStatus.FOUND:
        reasons.append("persistence_incomplete")
        return {
            "status": TRUST_DEGRADED,
            "reasons": reasons,
            "selected_evidence_count": selected_count,
            "candidate_count": candidate_count,
        }

    if view.rollup.failed_stages > 0:
        reasons.append("stage_failure")
        return {
            "status": TRUST_DEGRADED,
            "reasons": reasons,
            "selected_evidence_count": selected_count,
            "candidate_count": candidate_count,
        }

    if view.rollup.degraded_calls > 0:
        reasons.append("degraded_llm_calls")

    if selected_count == 0:
        reasons.append("no_selected_evidence")
    elif selected_count < 2:
        reasons.append("thin_selected_evidence")

    if candidate_count < 2:
        reasons.append("thin_candidate_pool")

    selected_candidates = artifact.evidence_candidates[:2] if artifact is not None else ()
    if compiled is not None and compiled.selected_evidence:
        authority_bands = [item.judgment.authority.band for item in compiled.selected_evidence if item.judgment is not None]
        selected_source_types = {candidate.source_type for candidate in selected_candidates}
        if authority_bands and not any(band in _STRONG_BANDS for band in authority_bands):
            reasons.append("low_confidence_selected_shape")
        elif "institutional" not in selected_source_types and selected_source_types <= {"unknown", "commentary", "vendor"}:
            reasons.append("low_confidence_selected_shape")

    if reasons:
        status = TRUST_WEAK if reasons == ["degraded_llm_calls"] else TRUST_NEEDS_REVIEW
    else:
        status = TRUST_USABLE

    return {
        "status": status,
        "reasons": reasons,
        "selected_evidence_count": selected_count,
        "candidate_count": candidate_count,
    }
