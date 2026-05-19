"""Local runtime config helpers for SourceTrace LLM wiring."""

from sourcetrace.llm import (
    LlmBootstrapConfig,
    LlmProfileConfig,
    LlmTaskConfig,
    SourceTraceLlmConfig,
)


def build_default_llm_config() -> SourceTraceLlmConfig:
    """Return the default local LLM task/bootstrap config for SourceTrace."""

    return SourceTraceLlmConfig(
        bootstrap=LlmBootstrapConfig(
            api_key_env_var="SOURCETRACE_LLM_API_KEY",
            base_url_env_var="SOURCETRACE_LLM_BASE_URL",
            api_version_env_var="SOURCETRACE_LLM_API_VERSION",
        ),
        default_timeout_seconds=30.0,
        default_max_output_tokens=1200,
        profiles={
            "claim_extraction_default": LlmProfileConfig(
                model="azure/gpt-4.1",
                temperature=0.0,
            ),
            "claim_normalization_default": LlmProfileConfig(
                model="azure/gpt-4.1",
                temperature=0.0,
                max_output_tokens=400,
            ),
            "credibility_assessment_default": LlmProfileConfig(
                model="azure/gpt-5.4",
                temperature=0.2,
                max_output_tokens=600,
            ),
        },
        tasks={
            "claim_extraction": LlmTaskConfig(
                profile="claim_extraction_default",
            ),
            "claim_normalization": LlmTaskConfig(
                profile="claim_normalization_default",
            ),
            "credibility_draft": LlmTaskConfig(
                profile="credibility_assessment_default",
            ),
        },
    )


__all__ = ["build_default_llm_config"]
