from __future__ import annotations

from sourcetrace_v2.core.domain.models import ResearchResultArtifact, RetrievedEvidenceCandidate


def _candidate_has_minimal_quality(candidate: RetrievedEvidenceCandidate) -> bool:
    return bool(candidate.title.strip() and candidate.url.strip() and candidate.snippet.strip())


def project_selected_evidence(*, artifact: ResearchResultArtifact | None, limit: int = 2) -> dict[str, object]:
    candidates = artifact.evidence_candidates if artifact is not None else ()
    ordered = tuple(sorted(candidates, key=lambda candidate: candidate.rank))
    quality_candidates = tuple(candidate for candidate in ordered if _candidate_has_minimal_quality(candidate))
    fallback_candidates = tuple(candidate for candidate in ordered if not _candidate_has_minimal_quality(candidate))
    selected = tuple((*quality_candidates, *fallback_candidates))[:limit]
    dropped = tuple(candidate for candidate in ordered if candidate not in selected)
    missing_snippet_dropped = sum(1 for candidate in dropped if not candidate.snippet.strip())
    return {
        "selected_count": len(selected),
        "selection_basis": "rank_with_minimal_content_guard",
        "selection_notes": [
            f"selected top {len(selected)} retrieval candidates after minimal content guard",
            "selection prefers candidates with non-empty title, url, and snippet before rank-only fallback",
        ] if selected else ["no retrieval candidates available for promotion"],
        "dropped_count": len(dropped),
        "rejected_reasons": [
            {
                "reason": "rank_limit",
                "count": len(dropped),
            },
            {
                "reason": "missing_minimal_content",
                "count": missing_snippet_dropped,
            },
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
