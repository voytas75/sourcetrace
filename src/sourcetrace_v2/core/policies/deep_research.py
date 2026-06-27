from __future__ import annotations

from sourcetrace_v2.core.domain.identifiers import StageId
from sourcetrace_v2.runtime.config.models import FeaturePolicy


def resolve_deep_research_stage_profile(*, policy: FeaturePolicy, stage_id: StageId) -> str:
    mapping = {
        StageId.PLANNING: policy.planning_profile,
        StageId.QUERY_REFINEMENT: policy.query_refinement_profile,
        StageId.EVIDENCE_JUDGE: policy.evidence_judge_profile,
        StageId.SYNTHESIS: policy.synthesis_profile,
    }
    return mapping[stage_id]
