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
    CredibilityDraftGateway,
    StructuredGenerationRuntime,
)
from sourcetrace.llm.litellm_client import (
    build_litellm_structured_generator,
    build_litellm_text_generator,
)
from sourcetrace.llm.models import LlmGenerationRequest, LlmMessage
from sourcetrace.llm.structured_generation import build_structured_generation_execution


@dataclass(frozen=True)
class SourceTraceLlmRuntime:
    """Assembled local LLM runtime entrypoints and resolved bootstrap inputs."""

    config: SourceTraceLlmConfig
    bootstrap: ResolvedLlmBootstrapConfig
    structured_generation: StructuredGenerationRuntime
    claim_extraction: ClaimExtractionGateway
    credibility_draft: CredibilityDraftGateway


def _build_credibility_draft_gateway(
    *,
    generate_text: Callable[[LlmGenerationRequest], Any],
    config: SourceTraceLlmConfig,
) -> CredibilityDraftGateway:
    def draft_credibility_note(evidence_summary: str):
        task = config.task("credibility_draft")
        return generate_text(
            LlmGenerationRequest(
                messages=(LlmMessage(role="user", content=evidence_summary),),
                model=task.model,
                temperature=task.temperature,
                max_output_tokens=task.max_output_tokens,
            )
        )

    return draft_credibility_note


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
    credibility_draft = _build_credibility_draft_gateway(
        generate_text=text_generator,
        config=config,
    )
    return SourceTraceLlmRuntime(
        config=config,
        bootstrap=bootstrap,
        structured_generation=structured_runtime,
        claim_extraction=claim_extraction,
        credibility_draft=credibility_draft,
    )


__all__ = [
    "SourceTraceLlmRuntime",
    "build_llm_runtime",
]
