import os

from sourcetrace.llm import LlmBootstrapConfig, LlmProfileConfig, LlmTaskConfig, SourceTraceLlmConfig
from sourcetrace.runtime_config import build_default_llm_config


def test_build_default_llm_config_uses_azure_base_url_when_only_legacy_base_url_is_present(
    monkeypatch,
) -> None:
    monkeypatch.delenv("SOURCETRACE_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ROOT_URL", raising=False)
    monkeypatch.setenv("AZURE_OPENAI_BASE_URL", "https://azure.example.test/openai/v1")

    config = build_default_llm_config()

    assert config.bootstrap.base_url_env_var == "AZURE_OPENAI_BASE_URL"


def test_build_default_llm_config_returns_expected_bootstrap_and_task_defaults(
    monkeypatch,
) -> None:
    monkeypatch.setenv("SOURCETRACE_LLM_BASE_URL", "https://llm.example.test")
    monkeypatch.delenv("AZURE_OPENAI_ROOT_URL", raising=False)
    config = build_default_llm_config()

    assert isinstance(config, SourceTraceLlmConfig)
    assert config.bootstrap == LlmBootstrapConfig(
        api_key_env_var="SOURCETRACE_LLM_API_KEY",
        base_url_env_var="SOURCETRACE_LLM_BASE_URL",
        api_version_env_var="SOURCETRACE_LLM_API_VERSION",
    )
    assert config.default_timeout_seconds == 30.0
    assert config.default_max_output_tokens == 1200
    assert config.profiles == {
        "claim_extraction_default": LlmProfileConfig(
            model="azure/gpt-5.4",
            temperature=0.0,
        ),
        "claim_normalization_default": LlmProfileConfig(
            model="azure/gpt-5.4",
            temperature=0.0,
            max_output_tokens=400,
        ),
        "credibility_assessment_default": LlmProfileConfig(
            model="azure/gpt-5.4",
            temperature=0.2,
            max_output_tokens=600,
        ),
        "research_synthesis_default": LlmProfileConfig(
            model="azure/gpt-5.4",
            temperature=0.2,
            max_output_tokens=900,
        ),
    }
    assert config.tasks == {
        "claim_extraction": LlmTaskConfig(
            profile="claim_extraction_default",
        ),
        "claim_normalization": LlmTaskConfig(
            profile="claim_normalization_default",
        ),
        "credibility_draft": LlmTaskConfig(
            profile="credibility_assessment_default",
        ),
        "research_synthesis": LlmTaskConfig(
            profile="research_synthesis_default",
        ),
    }
