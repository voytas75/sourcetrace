from sourcetrace.llm import LlmBootstrapConfig, LlmTaskConfig, SourceTraceLlmConfig
from sourcetrace.runtime_config import build_default_llm_config


def test_build_default_llm_config_returns_expected_bootstrap_and_task_defaults() -> None:
    config = build_default_llm_config()

    assert isinstance(config, SourceTraceLlmConfig)
    assert config.bootstrap == LlmBootstrapConfig(
        api_key_env_var="SOURCETRACE_LLM_API_KEY",
        base_url_env_var="SOURCETRACE_LLM_BASE_URL",
        api_version_env_var="SOURCETRACE_LLM_API_VERSION",
    )
    assert config.default_timeout_seconds == 30.0
    assert config.default_max_output_tokens == 1200
    assert config.tasks == {
        "claim_extraction": LlmTaskConfig(
            model="azure/gpt-4.1",
            temperature=0.0,
        ),
        "claim_normalization": LlmTaskConfig(
            model="azure/gpt-4.1",
            temperature=0.0,
            max_output_tokens=400,
        ),
        "credibility_draft": LlmTaskConfig(
            model="azure/gpt-5.4",
            temperature=0.2,
            max_output_tokens=600,
        ),
    }
