from __future__ import annotations

from sourcetrace_v2.core.policies.selected_evidence import (
    AUTHORITY_RELEVANCE_JUDGMENT_CONTRACT_V1,
    SELECTED_EVIDENCE_SELECTION_BASIS_V1,
    build_candidate_judgment,
    build_judgment_comparison,
    decide_selected_evidence,
)
from sourcetrace_v2.core.domain.models import ResearchResultArtifact, RetrievedEvidenceCandidate


def project_selected_evidence(*, artifact: ResearchResultArtifact | None, limit: int = 2) -> dict[str, object]:
    candidates = artifact.evidence_candidates if artifact is not None else ()
    decision = decide_selected_evidence(candidates, limit)
    selected = decision.selected
    dropped = decision.dropped
    selected_judgments = tuple((candidate.title, build_candidate_judgment(candidate)) for candidate in selected)
    return {
        "selected_count": len(selected),
        "selection_basis": SELECTED_EVIDENCE_SELECTION_BASIS_V1,
        "selection_notes": [
            f"selected top {len(selected)} retrieval candidates after minimal content guard and domain diversity pass",
            "selection prefers candidates with non-empty title, url, and snippet before rank-only fallback",
            "selection also prefers domain diversity when enough qualifying candidates exist",
        ] if selected else ["no retrieval candidates available for promotion"],
        "judgment_contract": {
            "version": AUTHORITY_RELEVANCE_JUDGMENT_CONTRACT_V1,
            "dimensions": ["authority", "topic_match", "specificity", "answer_fit"],
            "comparison": build_judgment_comparison(selected_judgments),
            "notes": [
                "judgment is provider-agnostic and derived from candidate query, title, url, and snippet",
            ],
        },
        "dropped_count": len(dropped),
        "rejected_reasons": [
            {
                "reason": "rank_limit",
                "count": len(dropped),
            },
            {
                "reason": "missing_minimal_content",
                "count": decision.missing_minimal_content_dropped,
            },
            {
                "reason": "domain_diversity_preference",
                "count": decision.domain_diversity_dropped,
            },
        ] if dropped else [],
        "items": [
            {
                "title": candidate.title,
                "url": candidate.url,
                "provider": candidate.provider,
                "rank": candidate.rank,
                "snippet": candidate.snippet,
                "judgment": _project_judgment(build_candidate_judgment(candidate)),
            }
            for candidate in selected
        ],
    }


def _project_judgment(judgment: object) -> dict[str, object]:
    return {
        "contract_version": judgment.contract_version,
        "authority": _project_dimension(judgment.authority),
        "topic_match": _project_dimension(judgment.topic_match),
        "specificity": _project_dimension(judgment.specificity),
        "answer_fit": _project_dimension(judgment.answer_fit),
    }


def _project_dimension(dimension: object) -> dict[str, object]:
    return {
        "score": dimension.score,
        "band": dimension.band,
        "signals": list(dimension.signals),
    }
