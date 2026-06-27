from sourcetrace_v2.core.domain.identifiers import StageId
from sourcetrace_v2.core.policies.deep_research import resolve_deep_research_stage_profile
from sourcetrace_v2.runtime.config.models import FeaturePolicy


def test_resolve_deep_research_stage_profile_uses_feature_policy() -> None:
    policy = FeaturePolicy(
        planning_profile="p1",
        query_refinement_profile="p2",
        evidence_judge_profile="p3",
        synthesis_profile="p4",
    )

    assert resolve_deep_research_stage_profile(policy=policy, stage_id=StageId.PLANNING) == "p1"
    assert resolve_deep_research_stage_profile(policy=policy, stage_id=StageId.QUERY_REFINEMENT) == "p2"
    assert resolve_deep_research_stage_profile(policy=policy, stage_id=StageId.EVIDENCE_JUDGE) == "p3"
    assert resolve_deep_research_stage_profile(policy=policy, stage_id=StageId.SYNTHESIS) == "p4"
