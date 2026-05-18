"""SourceTrace-owned protocols for LLM-backed task execution."""

from dataclasses import dataclass
from typing import Any, Protocol

from sourcetrace.llm.models import (
    LlmGenerationRequest,
    LlmGenerationResult,
    LlmMessage,
    LlmStructuredGenerationRequest,
    LlmStructuredGenerationResult,
)


class LlmTextGenerator(Protocol):
    """Provider-agnostic text generation seam."""

    def __call__(self, request: LlmGenerationRequest) -> LlmGenerationResult:
        ...


@dataclass(frozen=True)
class LlmTextGenerationExecution:
    """Explicit callable wiring bundle for text generation."""

    generate_text: LlmTextGenerator


class StructuredLlmGenerator(Protocol):
    """Provider-agnostic structured generation seam."""

    def __call__(
        self,
        request: LlmStructuredGenerationRequest,
    ) -> LlmStructuredGenerationResult:
        ...


@dataclass(frozen=True)
class StructuredLlmGenerationExecution:
    """Explicit callable wiring bundle for structured generation."""

    generate_structured: StructuredLlmGenerator


class StructuredGenerationExecutor(Protocol):
    """Task-aware structured generation seam bound to local config."""

    def __call__(
        self,
        *,
        task_name: str,
        schema_name: str,
        messages: tuple[LlmMessage, ...],
    ) -> LlmStructuredGenerationResult:
        ...


@dataclass(frozen=True)
class StructuredGenerationRuntime:
    """Bounded runtime bundle for task-aware structured generation."""

    generate_structured: StructuredGenerationExecutor


class ClaimExtractionGateway(Protocol):
    """Task-specific seam for extracting claims from prepared text."""

    def __call__(
        self,
        prepared_text: str,
    ) -> LlmStructuredGenerationResult:
        ...


class ClaimNormalizationGateway(Protocol):
    """Task-specific seam for normalizing extracted claim text."""

    def __call__(self, claim_text: str) -> LlmGenerationResult:
        ...


class CredibilityDraftGateway(Protocol):
    """Task-specific seam for drafting credibility notes."""

    def __call__(self, evidence_summary: str) -> LlmGenerationResult:
        ...


__all__ = [
    "ClaimExtractionGateway",
    "ClaimNormalizationGateway",
    "CredibilityDraftGateway",
    "LlmTextGenerationExecution",
    "LlmTextGenerator",
    "StructuredGenerationExecutor",
    "StructuredGenerationRuntime",
    "StructuredLlmGenerationExecution",
    "StructuredLlmGenerator",
]
