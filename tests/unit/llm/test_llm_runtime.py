import pytest

from sourcetrace.llm import (
    ClaimExtractionGateway,
    ClaimNormalizationGateway,
    CredibilityDraftGateway,
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
    SourceTraceLlmConfig,
    StructuredLlmGenerationExecution,
    build_claim_extraction_gateway,
    build_structured_generation_execution,
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
    assert not hasattr(extraction, "provider")


def test_source_trace_llm_config_raises_for_unknown_task_alias() -> None:
    config = SourceTraceLlmConfig(tasks={})

    with pytest.raises(LlmConfigurationError, match="missing LLM task config"):
        config.task("unknown")


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
