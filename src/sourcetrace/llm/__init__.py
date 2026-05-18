"""SourceTrace-owned LLM integration boundary."""

from sourcetrace.llm.config import (
    LlmBootstrapConfig,
    LlmTaskConfig,
    ResolvedLlmBootstrapConfig,
    SourceTraceLlmConfig,
    resolve_llm_bootstrap_config,
)
from sourcetrace.llm.errors import (
    LlmConfigurationError,
    LlmError,
    LlmProviderError,
    LlmRateLimitError,
    LlmSchemaError,
    LlmTimeoutError,
)
from sourcetrace.llm.extraction import build_claim_extraction_gateway
from sourcetrace.llm.interfaces import (
    ClaimExtractionGateway,
    ClaimNormalizationGateway,
    CredibilityDraftGateway,
    LlmTextGenerationExecution,
    LlmTextGenerator,
    StructuredGenerationRuntime,
    StructuredLlmGenerationExecution,
    StructuredLlmGenerator,
)
from sourcetrace.llm.litellm_client import (
    build_litellm_completion_caller,
    build_litellm_structured_generator,
    build_litellm_text_generator,
)
from sourcetrace.llm.models import (
    LlmGenerationRequest,
    LlmGenerationResult,
    LlmMessage,
    LlmStructuredGenerationRequest,
    LlmStructuredGenerationResult,
    TokenUsage,
)
from sourcetrace.llm.structured_generation import build_structured_generation_execution

__all__ = [
    "ClaimExtractionGateway",
    "ClaimNormalizationGateway",
    "CredibilityDraftGateway",
    "LlmBootstrapConfig",
    "LlmConfigurationError",
    "LlmError",
    "LlmGenerationRequest",
    "LlmGenerationResult",
    "LlmMessage",
    "LlmProviderError",
    "LlmRateLimitError",
    "LlmSchemaError",
    "LlmStructuredGenerationRequest",
    "LlmStructuredGenerationResult",
    "LlmTaskConfig",
    "LlmTextGenerationExecution",
    "LlmTextGenerator",
    "LlmTimeoutError",
    "ResolvedLlmBootstrapConfig",
    "SourceTraceLlmConfig",
    "StructuredGenerationRuntime",
    "StructuredLlmGenerationExecution",
    "StructuredLlmGenerator",
    "TokenUsage",
    "build_claim_extraction_gateway",
    "build_litellm_completion_caller",
    "build_litellm_structured_generator",
    "build_litellm_text_generator",
    "build_structured_generation_execution",
    "resolve_llm_bootstrap_config",
]
