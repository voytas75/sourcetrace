from __future__ import annotations

from sourcetrace_v2.runtime.config.models import FeaturePolicy, LoggingPolicy, RuntimeConfig, RuntimeProfile


def build_default_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        profiles={
            "planning_default": RuntimeProfile(name="planning_default", provider="azure", model="gpt-5.4", provider_model_id="gpt-5.4", mode="structured"),
            "research_fast": RuntimeProfile(name="research_fast", provider="azure", model="gpt-5.4-mini", provider_model_id="gpt-5.4-mini", temperature=1.0),
            "judge_strict": RuntimeProfile(name="judge_strict", provider="azure", model="gpt-5.4", provider_model_id="gpt-5.4", mode="structured"),
            "synthesis_default": RuntimeProfile(name="synthesis_default", provider="azure", model="gpt-5.4", provider_model_id="gpt-5.4"),
        },
        deep_research=FeaturePolicy(),
        logging=LoggingPolicy(),
    )
