from __future__ import annotations

from sourcetrace_v2.core.domain.models import ResearchResultArtifact, RetrievedEvidenceCandidate


def project_selected_evidence(*, artifact: ResearchResultArtifact | None, limit: int = 2) -> dict[str, object]:
    candidates = artifact.evidence_candidates if artifact is not None else ()
    ordered = tuple(sorted(candidates, key=lambda candidate: candidate.rank))
    selected = ordered[:limit]
    dropped = ordered[limit:]
    return {
        "selected_count": len(selected),
        "selection_basis": "top_ranked_retrieval_candidates",
        "selection_notes": [
            f"selected top {len(selected)} ranked retrieval candidates",
            "selection currently uses deterministic rank-only carry-forward",
        ] if selected else ["no retrieval candidates available for promotion"],
        "dropped_count": len(dropped),
        "rejected_reasons": [
            {
                "reason": "rank_limit",
                "count": len(dropped),
            }
        ] if dropped else [],
        "items": [
            {
                "title": candidate.title,
                "url": candidate.url,
                "provider": candidate.provider,
                "rank": candidate.rank,
                "snippet": candidate.snippet,
            }
            for candidate in selected
        ],
    }
