from dataclasses import FrozenInstanceError
from typing import Any

import pytest

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
    LlmTextGenerationExecution,
    LlmTextGenerator,
    LlmTimeoutError,
    SourceTraceLlmConfig,
    StructuredGenerationRuntime,
    StructuredLlmGenerationExecution,
    StructuredLlmGenerator,
    TokenUsage,
)
from sourcetrace.llm.interfaces import (
    ClaimExtractionGateway as InterfacesClaimExtractionGateway,
)
from sourcetrace.llm.interfaces import (
    ClaimNormalizationGateway as InterfacesClaimNormalizationGateway,
)
from sourcetrace.llm.interfaces import (
    CredibilityDraftGateway as InterfacesCredibilityDraftGateway,
)
from sourcetrace.llm.interfaces import LlmTextGenerator as InterfacesLlmTextGenerator
from sourcetrace.llm.interfaces import (
    StructuredLlmGenerator as InterfacesStructuredLlmGenerator,
)


def test_llm_package_re_exports_models_and_execution_seams() -> None:
    assert LlmTextGenerator is InterfacesLlmTextGenerator
    assert StructuredLlmGenerator is InterfacesStructuredLlmGenerator
    assert ClaimExtractionGateway is InterfacesClaimExtractionGateway
    assert ClaimNormalizationGateway is InterfacesClaimNormalizationGateway
    assert CredibilityDraftGateway is InterfacesCredibilityDraftGateway


@pytest.mark.parametrize(
    ("model", "expected_fields"),
    [
        (LlmMessage, ("role", "content")),
        (
            LlmGenerationRequest,
            ("messages", "model", "temperature", "max_output_tokens"),
        ),
        (
            LlmGenerationResult,
            ("text", "model", "finish_reason", "usage"),
        ),
        (
            LlmStructuredGenerationRequest,
            ("messages", "model", "schema_name", "temperature", "max_output_tokens"),
        ),
        (
            LlmStructuredGenerationResult,
            ("payload", "model", "finish_reason", "usage"),
        ),
        (TokenUsage, ("input_tokens", "output_tokens", "total_tokens")),
        (LlmTextGenerationExecution, ("generate_text",)),
        (StructuredLlmGenerationExecution, ("generate_structured",)),
        (StructuredGenerationRuntime, ("generate_structured",)),
        (LlmBootstrapConfig, ("api_key_env_var", "base_url_env_var")),
        (LlmTaskConfig, ("model", "temperature", "max_output_tokens")),
        (
            SourceTraceLlmConfig,
            ("default_timeout_seconds", "default_max_output_tokens", "bootstrap", "tasks"),
        ),
    ],
)
def test_llm_records_and_execution_bundles_are_frozen_dataclasses(
    model: type[Any],
    expected_fields: tuple[str, ...],
) -> None:
    assert getattr(model, "__dataclass_fields__", None) is not None
    assert tuple(model.__dataclass_fields__) == expected_fields


def test_llm_execution_bundles_are_immutable() -> None:
    def generate_text(request: LlmGenerationRequest) -> LlmGenerationResult:
        return LlmGenerationResult(text="ok", model=request.model)

    execution = LlmTextGenerationExecution(generate_text=generate_text)
    runtime = StructuredGenerationRuntime(
        generate_structured=lambda *, task_name, schema_name, messages: LlmStructuredGenerationResult(
            payload={"ok": True},
            model=task_name,
        )
    )

    with pytest.raises(FrozenInstanceError):
        setattr(execution, "generate_text", generate_text)

    with pytest.raises(FrozenInstanceError):
        setattr(runtime, "generate_structured", runtime.generate_structured)


@pytest.mark.parametrize(
    "protocol",
    [
        LlmTextGenerator,
        StructuredLlmGenerator,
        ClaimExtractionGateway,
        ClaimNormalizationGateway,
        CredibilityDraftGateway,
    ],
)
def test_llm_protocols_expose_callable_entrypoints(protocol: type[Any]) -> None:
    assert getattr(protocol, "_is_protocol", False) is True
    assert callable(protocol.__call__)


def test_llm_request_and_result_objects_keep_provider_details_outside_interface() -> None:
    for exported in (
        LlmBootstrapConfig,
        LlmError,
        LlmTimeoutError,
        LlmRateLimitError,
        LlmProviderError,
        LlmSchemaError,
        LlmConfigurationError,
        LlmTaskConfig,
        SourceTraceLlmConfig,
    ):
        assert exported is not None

    request = LlmGenerationRequest(
        messages=(LlmMessage(role="user", content="extract claims"),),
        model="claims-fast",
        temperature=0.0,
        max_output_tokens=512,
    )
    result = LlmGenerationResult(
        text='{"claims": []}',
        model="claims-fast",
        finish_reason="stop",
        usage=TokenUsage(input_tokens=10, output_tokens=4, total_tokens=14),
    )

    assert request.messages[0].content == "extract claims"
    assert result.usage.total_tokens == 14
    assert not hasattr(request, "provider")
    assert not hasattr(request, "api_key")
    assert not hasattr(result, "provider_response")


def test_bootstrap_config_keeps_env_contract_explicit_but_outside_request_surface() -> None:
    bootstrap = LlmBootstrapConfig(
        api_key_env_var="SOURCETRACE_LLM_API_KEY",
        base_url_env_var="SOURCETRACE_LLM_BASE_URL",
    )
    config = SourceTraceLlmConfig(bootstrap=bootstrap)

    assert config.bootstrap is bootstrap
    assert config.bootstrap_env_var_names() == (
        "SOURCETRACE_LLM_API_KEY",
        "SOURCETRACE_LLM_BASE_URL",
    )
