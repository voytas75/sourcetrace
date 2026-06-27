from __future__ import annotations

from sourcetrace_v2.core.domain.models import ResearchResultArtifact, RetrievedEvidenceCandidate


def project_selected_evidence(*, artifact: ResearchResultArtifact | None, limit: int = 2) -> dict[str, object]:
    candidates = artifact.evidence_candidates if artifact is not None else ()
    selected = tuple(sorted(candidates, key=lambda candidate: candidate.rank))[:limit]
    return {
        "selected_count": len(selected),
        "selection_basis": "top_ranked_retrieval_candidates",
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
