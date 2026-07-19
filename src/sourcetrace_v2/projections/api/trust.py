from __future__ import annotations

from sourcetrace_v2.core.contracts.compiled_artifacts import CompiledEvidenceSnapshot
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
    candidate_pool_count = (
        artifact.retrieval_candidate_pool_count
        if artifact is not None and artifact.retrieval_candidate_pool_count > 0
        else (len(artifact.pretrim_evidence_candidates) if artifact is not None and artifact.pretrim_evidence_candidates else candidate_count)
    )

    reasons: list[str] = []

    if view.status is not PersistedViewStatus.FOUND:
        reasons.append("persistence_incomplete")
        return {
            "status": TRUST_DEGRADED,
            "reasons": reasons,
            "selected_evidence_count": selected_count,
            "candidate_count": candidate_count,
            "retrieval_candidate_pool_count": candidate_pool_count,
            "pretrim_candidate_count": candidate_pool_count,
        }

    if view.rollup.failed_stages > 0:
        reasons.append("stage_failure")
        return {
            "status": TRUST_DEGRADED,
            "reasons": reasons,
            "selected_evidence_count": selected_count,
            "candidate_count": candidate_count,
            "retrieval_candidate_pool_count": candidate_pool_count,
            "pretrim_candidate_count": candidate_pool_count,
        }

    diagnostics = artifact.retrieval_diagnostics if artifact is not None else None
    if diagnostics is not None and diagnostics.pretrim_explicit and diagnostics.pretrim.status == "insufficient":
        return {
            "status": TRUST_NEEDS_REVIEW,
            "reasons": ["retrieval_insufficient_semantic_fit"],
            "selected_evidence_count": selected_count,
            "candidate_count": candidate_count,
            "retrieval_candidate_pool_count": candidate_pool_count,
            "pretrim_candidate_count": candidate_pool_count,
        }

    if artifact is not None and diagnostics is None and artifact.retrieval_semantic_fit_status == "insufficient":
        return {
            "status": TRUST_NEEDS_REVIEW,
            "reasons": ["retrieval_insufficient_semantic_fit"],
            "selected_evidence_count": selected_count,
            "candidate_count": candidate_count,
            "retrieval_candidate_pool_count": candidate_pool_count,
            "pretrim_candidate_count": candidate_pool_count,
        }

    if view.rollup.degraded_calls > 0:
        reasons.append("degraded_llm_calls")

    if selected_count == 0:
        reasons.append("no_selected_evidence")
    elif selected_count < 2:
        reasons.append("thin_selected_evidence")

    if candidate_count < 2:
        reasons.append("thin_candidate_pool")

    selected_candidates = tuple(compiled.selected_evidence) if compiled is not None and compiled.selected_evidence else ()
    if selected_candidates:
        authority_bands = [item.judgment.authority.band for item in selected_candidates if item.judgment is not None]
        selected_source_types = {_source_type_from_compiled_candidate(item) for item in selected_candidates}
        if authority_bands and not any(band in _STRONG_BANDS for band in authority_bands):
            reasons.append("low_confidence_selected_shape")
        elif "institutional" not in selected_source_types and selected_source_types <= {"unknown", "commentary", "vendor"}:
            reasons.append("low_confidence_selected_shape")
        elif _selected_institutional_pair_has_explicit_jurisdiction_mismatch(selected_candidates):
            reasons.append("jurisdiction_mixed_selected_institutional_pair")
        elif _selected_candidates_have_strong_authority_but_weak_fit(selected_candidates):
            reasons.append("strong_authority_but_weak_fit_selected_shape")

    if reasons:
        status = TRUST_WEAK if reasons == ["degraded_llm_calls"] else TRUST_NEEDS_REVIEW
    else:
        status = TRUST_USABLE

    return {
        "status": status,
        "reasons": reasons,
        "selected_evidence_count": selected_count,
        "candidate_count": candidate_count,
        "retrieval_candidate_pool_count": candidate_pool_count,
        "pretrim_candidate_count": candidate_pool_count,
    }


def _selected_institutional_pair_has_explicit_jurisdiction_mismatch(
    selected_candidates: tuple[CompiledEvidenceSnapshot, ...],
) -> bool:
    if len(selected_candidates) < 2:
        return False
    if any(_source_type_from_compiled_candidate(candidate) != "institutional" for candidate in selected_candidates):
        return False

    jurisdiction_ids = [_trusted_jurisdiction_id(candidate) for candidate in selected_candidates]
    if any(jurisdiction_id is None for jurisdiction_id in jurisdiction_ids):
        return False
    return len(set(jurisdiction_ids)) > 1


def _trusted_jurisdiction_id(candidate: CompiledEvidenceSnapshot) -> str | None:
    """Use only explicit, sufficiently confident jurisdiction metadata.

    Hosts, titles, public suffixes, and differing authority IDs are source cues,
    not jurisdiction evidence. Unknown metadata must remain non-blocking rather
    than fabricating a jurisdiction claim.
    """
    metadata = candidate.trust_metadata
    if metadata is None or metadata.confidence not in {"high", "medium"}:
        return None
    jurisdiction_id = metadata.jurisdiction_id.strip().casefold()
    return jurisdiction_id or None


def _selected_candidates_have_strong_authority_but_weak_fit(
    selected_candidates: tuple[CompiledEvidenceSnapshot, ...],
) -> bool:
    if len(selected_candidates) < 2:
        return False

    judgments = tuple(candidate.judgment for candidate in selected_candidates if candidate.judgment is not None)
    if len(judgments) != len(selected_candidates):
        return False

    if not all(judgment.authority.band in _STRONG_BANDS for judgment in judgments):
        return False
    if not all(judgment.answer_fit.band in _LOW_BANDS for judgment in judgments):
        return False

    topic_match_weak = all(judgment.topic_match.band in _LOW_BANDS for judgment in judgments)
    specificity_weak = all(judgment.specificity.band in _LOW_BANDS for judgment in judgments)
    return topic_match_weak or specificity_weak



def _source_type_from_compiled_candidate(candidate: CompiledEvidenceSnapshot) -> str:
    if candidate.judgment is None:
        return "unknown"
    if candidate.judgment.authority.band in _STRONG_BANDS:
        return "institutional"
    if candidate.judgment.authority.band in _LOW_BANDS:
        return "unknown"
    return "vendor"
