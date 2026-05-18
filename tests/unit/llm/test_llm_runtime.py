import pytest
from os import environ

from sourcetrace.llm import (
    ClaimExtractionGateway,
    ClaimNormalizationGateway,
    CredibilityDraftGateway,
    LlmBootstrapConfig,
    LlmConfigurationError,
    LlmError,
    LlmGenerationRequest,
    LlmGenerationResult,
    LlmMessage,
    LlmProviderError,
    LlmRateLimitError,
    LlmSchemaError,
    LlmStructuredGenerationRequest,
    LlmStructuredGenerationResult,
    LlmTaskConfig,
    LlmTimeoutError,
    ResolvedLlmBootstrapConfig,
    SourceTraceLlmConfig,
    StructuredLlmGenerationExecution,
    build_claim_extraction_gateway,
    build_llm_runtime,
    build_structured_generation_execution,
    resolve_llm_bootstrap_config,
)
from sourcetrace.llm.errors import map_litellm_error
from sourcetrace.llm.models import TokenUsage


class _FakeTimeoutError(Exception):
    pass


class _FakeRateLimitError(Exception):
    pass


class _FakeBadRequestError(Exception):
    pass


def test_llm_error_package_exports_are_stable() -> None:
    for exported in (
        LlmError,
        LlmTimeoutError,
        LlmRateLimitError,
        LlmProviderError,
        LlmSchemaError,
        LlmConfigurationError,
        LlmTaskConfig,
        SourceTraceLlmConfig,
        build_structured_generation_execution,
        build_claim_extraction_gateway,
    ):
        assert exported is not None


def test_litellm_error_mapping_normalizes_timeout_and_rate_limit_categories() -> None:
    timeout = map_litellm_error(_FakeTimeoutError("request timed out"))
    rate_limit = map_litellm_error(_FakeRateLimitError("too many requests"))
    provider = map_litellm_error(_FakeBadRequestError("invalid request payload"))

    assert isinstance(timeout, LlmTimeoutError)
    assert isinstance(rate_limit, LlmRateLimitError)
    assert isinstance(provider, LlmProviderError)
    assert "_FakeBadRequestError" in str(provider)


def test_source_trace_llm_config_returns_task_mapping_without_provider_leakage() -> None:
    config = SourceTraceLlmConfig(
        default_timeout_seconds=30.0,
        default_max_output_tokens=1024,
        bootstrap=LlmBootstrapConfig(
            api_key_env_var="SOURCETRACE_LLM_API_KEY",
            base_url_env_var="SOURCETRACE_LLM_BASE_URL",
        ),
        tasks={
            "claim_extraction": LlmTaskConfig(
                model="gpt-4o-mini",
                temperature=0.0,
                max_output_tokens=800,
            ),
            "credibility_draft": LlmTaskConfig(
                model="gpt-4.1-mini",
                temperature=0.2,
            ),
        },
    )

    extraction = config.task("claim_extraction")

    assert extraction.model == "gpt-4o-mini"
    assert extraction.temperature == 0.0
    assert extraction.max_output_tokens == 800
    assert config.bootstrap_env_var_names() == (
        "SOURCETRACE_LLM_API_KEY",
        "SOURCETRACE_LLM_BASE_URL",
    )
    assert not hasattr(extraction, "provider")


def test_source_trace_llm_config_raises_for_unknown_task_alias() -> None:
    config = SourceTraceLlmConfig(tasks={})

    with pytest.raises(LlmConfigurationError, match="missing LLM task config"):
        config.task("unknown")


def test_source_trace_llm_config_defaults_to_no_bootstrap_env_vars() -> None:
    config = SourceTraceLlmConfig(tasks={})

    assert config.bootstrap_env_var_names() == ()


def test_bootstrap_resolver_returns_empty_values_when_no_env_vars_are_declared() -> None:
    resolved = resolve_llm_bootstrap_config(LlmBootstrapConfig())

    assert resolved == ResolvedLlmBootstrapConfig()


def test_bootstrap_resolver_raises_for_missing_declared_env_var() -> None:
    bootstrap = LlmBootstrapConfig(api_key_env_var="SOURCETRACE_LLM_API_KEY")
    original_api_key = environ.get("SOURCETRACE_LLM_API_KEY")

    try:
        environ.pop("SOURCETRACE_LLM_API_KEY", None)

        with pytest.raises(
            LlmConfigurationError,
            match="missing required LLM bootstrap env var for api_key: SOURCETRACE_LLM_API_KEY",
        ):
            resolve_llm_bootstrap_config(bootstrap)
    finally:
        if original_api_key is None:
            environ.pop("SOURCETRACE_LLM_API_KEY", None)
        else:
            environ["SOURCETRACE_LLM_API_KEY"] = original_api_key


def test_bootstrap_resolver_raises_for_blank_declared_env_var() -> None:
    bootstrap = LlmBootstrapConfig(base_url_env_var="SOURCETRACE_LLM_BASE_URL")
    original_base_url = environ.get("SOURCETRACE_LLM_BASE_URL")

    try:
        environ["SOURCETRACE_LLM_BASE_URL"] = "   "

        with pytest.raises(
            LlmConfigurationError,
            match="missing required LLM bootstrap env var for base_url: SOURCETRACE_LLM_BASE_URL",
        ):
            resolve_llm_bootstrap_config(bootstrap)
    finally:
        if original_base_url is None:
            environ.pop("SOURCETRACE_LLM_BASE_URL", None)
        else:
            environ["SOURCETRACE_LLM_BASE_URL"] = original_base_url


def test_build_llm_runtime_assembles_bootstrap_structured_generation_and_claim_gateway() -> None:
    config = SourceTraceLlmConfig(
        bootstrap=LlmBootstrapConfig(
            api_key_env_var="SOURCETRACE_LLM_API_KEY",
            base_url_env_var="SOURCETRACE_LLM_BASE_URL",
        ),
        tasks={"claim_extraction": LlmTaskConfig(model="gpt-4o-mini", temperature=0.0)},
    )
    original_api_key = environ.get("SOURCETRACE_LLM_API_KEY")
    original_base_url = environ.get("SOURCETRACE_LLM_BASE_URL")
    captured_kwargs: dict[str, object] = {}

    def completion_fn(**kwargs: object) -> dict[str, object]:
        captured_kwargs.update(kwargs)
        return {
            "model": kwargs["model"],
            "choices": [
                {
                    "message": {
                        "parsed": {
                            "claims": [
                                {
                                    "claim_id": "claim-1",
                                    "chunk_id": "chunk-1",
                                    "exact_text": "alpha claim",
                                    "source_span_reference": "chars:0-11",
                                }
                            ]
                        }
                    },
                    "finish_reason": "stop",
                }
            ],
        }

    try:
        environ["SOURCETRACE_LLM_API_KEY"] = "test-api-key"
        environ["SOURCETRACE_LLM_BASE_URL"] = "https://llm.example.test"

        runtime = build_llm_runtime(completion_fn=completion_fn, config=config)
        result = runtime.claim_extraction("alpha claim in source text")

        assert runtime.config is config
        assert runtime.bootstrap == ResolvedLlmBootstrapConfig(
            api_key="test-api-key",
            base_url="https://llm.example.test",
        )
        assert captured_kwargs["api_key"] == "test-api-key"
        assert captured_kwargs["base_url"] == "https://llm.example.test"
        assert captured_kwargs["model"] == "gpt-4o-mini"
        assert result.payload["claims"][0]["claim_id"] == "claim-1"
    finally:
        if original_api_key is None:
            environ.pop("SOURCETRACE_LLM_API_KEY", None)
        else:
            environ["SOURCETRACE_LLM_API_KEY"] = original_api_key

        if original_base_url is None:
            environ.pop("SOURCETRACE_LLM_BASE_URL", None)
        else:
            environ["SOURCETRACE_LLM_BASE_URL"] = original_base_url


def test_structured_generation_execution_builds_schema_aware_request_and_parses_payload() -> None:
    captured_request: LlmStructuredGenerationRequest | None = None

    def generate_structured(
        request: LlmStructuredGenerationRequest,
    ) -> LlmStructuredGenerationResult:
        nonlocal captured_request
        captured_request = request
        return LlmStructuredGenerationResult(
            payload={"claims": [{"claim_text": "alpha"}]},
            model=request.model,
            finish_reason="stop",
            usage=TokenUsage(input_tokens=12, output_tokens=6, total_tokens=18),
        )

    config = SourceTraceLlmConfig(
        tasks={
            "claim_extraction": LlmTaskConfig(
                model="gpt-4o-mini",
                temperature=0.0,
                max_output_tokens=600,
            )
        }
    )
    execution = build_structured_generation_execution(
        generate_structured=generate_structured,
        config=config,
    )

    result = execution.generate_structured(
        task_name="claim_extraction",
        schema_name="ClaimExtractionPayload",
        messages=(LlmMessage(role="user", content="extract claims from text"),),
    )

    assert captured_request is not None
    assert captured_request.model == "gpt-4o-mini"
    assert captured_request.schema_name == "ClaimExtractionPayload"
    assert captured_request.max_output_tokens == 600
    assert result.payload["claims"][0]["claim_text"] == "alpha"
    assert result.usage.total_tokens == 18


def test_structured_generation_execution_maps_invalid_payload_to_schema_error() -> None:
    def generate_structured(
        request: LlmStructuredGenerationRequest,
    ) -> LlmStructuredGenerationResult:
        return LlmStructuredGenerationResult(payload=None, model=request.model)

    config = SourceTraceLlmConfig(
        tasks={"claim_extraction": LlmTaskConfig(model="gpt-4o-mini")}
    )
    execution = build_structured_generation_execution(
        generate_structured=generate_structured,
        config=config,
    )

    with pytest.raises(LlmSchemaError, match="must be a mapping"):
        execution.generate_structured(
            task_name="claim_extraction",
            schema_name="ClaimExtractionPayload",
            messages=(LlmMessage(role="user", content="extract claims from text"),),
        )


def test_claim_extraction_gateway_uses_structured_generation_contract() -> None:
    captured_request: LlmGenerationRequest | None = None

    def generate_structured(
        request: LlmStructuredGenerationRequest,
    ) -> LlmStructuredGenerationResult:
        return LlmStructuredGenerationResult(
            payload={
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "chunk_id": "chunk-1",
                        "exact_text": "alpha claim",
                        "source_span_reference": "chars:0-11",
                    }
                ]
            },
            model=request.model,
        )

    config = SourceTraceLlmConfig(
        tasks={"claim_extraction": LlmTaskConfig(model="gpt-4o-mini", temperature=0.0)}
    )
    execution = build_structured_generation_execution(
        generate_structured=generate_structured,
        config=config,
    )
    gateway = build_claim_extraction_gateway(execution=execution)

    result = gateway(
        prepared_text="alpha claim in source text",
    )

    assert result.payload["claims"][0]["claim_id"] == "claim-1"
    assert result.payload["claims"][0]["source_span_reference"] == "chars:0-11"


@pytest.mark.parametrize(
    ("gateway", "input_text"),
    [
        (
            ClaimNormalizationGateway,
            "normalize this claim",
        ),
        (
            CredibilityDraftGateway,
            "draft credibility note",
        ),
    ],
)
def test_task_specific_text_gateways_remain_protocol_surfaces(
    gateway: type[object],
    input_text: str,
) -> None:
    assert getattr(gateway, "_is_protocol", False) is True
    assert callable(gateway.__call__)
    assert input_text
