from __future__ import annotations

from sourcetrace_v2.core.domain.models import ResearchResultArtifact, RetrievalPoolSemanticFitSnapshot


def _snapshot(snapshot: RetrievalPoolSemanticFitSnapshot) -> dict[str, object]:
    return {
        "status": snapshot.status,
        "focus_term_count": snapshot.focus_term_count,
        "matched_term_count": snapshot.matched_term_count,
        "matched_terms": list(snapshot.matched_terms),
        "best_candidate_rank": snapshot.best_candidate_rank,
    }


def project_retrieval_semantic_fit_diagnostics(*, artifact: ResearchResultArtifact | None) -> dict[str, object] | None:
    if artifact is None:
        return None
    if artifact.retrieval_diagnostics is None:
        return {
            "available": False,
            "contract_version": "retrieval-semantic-fit-guard-v1",
            "focus_terms": [],
            "pretrim": None,
            "trimmed": None,
            "insufficiency_stage": "unknown",
            "pretrim_pool_source": "legacy_trimmed_fallback",
        }
    diagnostics = artifact.retrieval_diagnostics
    return {
        "available": True,
        "contract_version": diagnostics.contract_version,
        "focus_terms": list(diagnostics.focus_terms),
        "pretrim": _snapshot(diagnostics.pretrim),
        "trimmed": _snapshot(diagnostics.trimmed),
        "insufficiency_stage": diagnostics.insufficiency_stage,
        "pretrim_pool_source": "explicit" if diagnostics.pretrim_explicit else "legacy_trimmed_fallback",
    }
