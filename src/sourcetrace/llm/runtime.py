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
from sourcetrace.llm.interfaces import (
    ClaimExtractionGateway,
    ClaimNormalizationGateway,
    CredibilityDraftGateway,
    StructuredGenerationRuntime,
)
from sourcetrace.llm.litellm_client import (
    build_litellm_structured_generator,
    build_litellm_text_generator,
)
from sourcetrace.llm.models import LlmGenerationRequest, LlmGenerationResult, LlmMessage
from sourcetrace.llm.structured_generation import build_structured_generation_execution


@dataclass(frozen=True)
class SourceTraceLlmRuntime:
    """Assembled local LLM runtime entrypoints and resolved bootstrap inputs."""

    config: SourceTraceLlmConfig
    bootstrap: ResolvedLlmBootstrapConfig
    structured_generation: StructuredGenerationRuntime
    claim_extraction: ClaimExtractionGateway
    claim_normalization: ClaimNormalizationGateway
    credibility_draft: CredibilityDraftGateway
    research_synthesis: CredibilityDraftGateway


def _build_text_task_gateway(
    *,
    task_name: str,
    generate_text: Callable[[LlmGenerationRequest], LlmGenerationResult],
    config: SourceTraceLlmConfig,
) -> Callable[..., LlmGenerationResult]:
    def invoke(input_text: str) -> LlmGenerationResult:
        task = config.task(task_name)
        return generate_text(
            LlmGenerationRequest(
                messages=(LlmMessage(role="user", content=input_text),),
                model=task.model,
                temperature=task.temperature,
                max_output_tokens=task.max_output_tokens,
            )
        )

    return invoke


def build_llm_runtime(
    *,
    completion_fn: Callable[..., dict[str, Any]],
    config: SourceTraceLlmConfig,
) -> SourceTraceLlmRuntime:
    """Assemble the minimal LLM runtime from config, env bootstrap, and LiteLLM helpers."""

    bootstrap = resolve_llm_bootstrap_config(config.bootstrap)
    text_generator = build_litellm_text_generator(
        completion_fn=completion_fn,
        bootstrap=bootstrap,
    )
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
    claim_normalization = _build_text_task_gateway(
        task_name="claim_normalization",
        generate_text=text_generator,
        config=config,
    )
    credibility_draft = _build_text_task_gateway(
        task_name="credibility_draft",
        generate_text=text_generator,
        config=config,
    )
    research_synthesis = _build_text_task_gateway(
        task_name="research_synthesis",
        generate_text=text_generator,
        config=config,
    )
    return SourceTraceLlmRuntime(
        config=config,
        bootstrap=bootstrap,
        structured_generation=structured_runtime,
        claim_extraction=claim_extraction,
        claim_normalization=claim_normalization,
        credibility_draft=credibility_draft,
        research_synthesis=research_synthesis,
    )


__all__ = [
    "SourceTraceLlmRuntime",
    "build_llm_runtime",
]
