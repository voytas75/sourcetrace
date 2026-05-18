"""Small runtime assembly helpers for SourceTrace-owned LLM wiring."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sourcetrace.llm.config import (
    ResolvedLlmBootstrapConfig,
    SourceTraceLlmConfig,
    resolve_llm_bootstrap_config,
)
from sourcetrace.llm.extraction import build_claim_extraction_gateway
from sourcetrace.llm.interfaces import ClaimExtractionGateway, StructuredGenerationRuntime
from sourcetrace.llm.litellm_client import build_litellm_structured_generator
from sourcetrace.llm.structured_generation import build_structured_generation_execution


@dataclass(frozen=True)
class SourceTraceLlmRuntime:
    """Assembled local LLM runtime entrypoints and resolved bootstrap inputs."""

    config: SourceTraceLlmConfig
    bootstrap: ResolvedLlmBootstrapConfig
    structured_generation: StructuredGenerationRuntime
    claim_extraction: ClaimExtractionGateway


def build_llm_runtime(
    *,
    completion_fn: Callable[..., dict[str, Any]],
    config: SourceTraceLlmConfig,
) -> SourceTraceLlmRuntime:
    """Assemble the minimal LLM runtime from config, env bootstrap, and LiteLLM helpers."""

    bootstrap = resolve_llm_bootstrap_config(config.bootstrap)
    structured_generator = build_litellm_structured_generator(
        completion_fn=completion_fn,
        bootstrap=bootstrap,
    )
    structured_execution = build_structured_generation_execution(
        generate_structured=structured_generator,
        config=config,
    )
    structured_runtime = StructuredGenerationRuntime(
        generate_structured=structured_execution.generate_structured,
    )
    claim_extraction = build_claim_extraction_gateway(execution=structured_runtime)
    return SourceTraceLlmRuntime(
        config=config,
        bootstrap=bootstrap,
        structured_generation=structured_runtime,
        claim_extraction=claim_extraction,
    )


__all__ = [
    "SourceTraceLlmRuntime",
    "build_llm_runtime",
]
