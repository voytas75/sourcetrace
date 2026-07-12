from __future__ import annotations

from sourcetrace_v2.runtime.config.models import FeaturePolicy, LoggingPolicy, RuntimeConfig, RuntimeProfile


def build_default_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        profiles={
            "planning_default": RuntimeProfile(name="planning_default", provider="azure", model="gpt-5.4", provider_model_id="gpt-5.4", mode="structured", max_output_tokens=1200),
            "research_fast": RuntimeProfile(name="research_fast", provider="azure", model="gpt-5.4-mini", provider_model_id="gpt-5.4-mini", temperature=1.0, max_output_tokens=300),
            "judge_strict": RuntimeProfile(name="judge_strict", provider="azure", model="gpt-5.4", provider_model_id="gpt-5.4", mode="structured", max_output_tokens=1400),
            "synthesis_default": RuntimeProfile(name="synthesis_default", provider="azure", model="gpt-5.4", provider_model_id="gpt-5.4", max_output_tokens=2200),
        },
        deep_research=FeaturePolicy(),
        logging=LoggingPolicy(),
    )
