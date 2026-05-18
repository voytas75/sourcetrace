"""Provider-neutral LLM request and result records."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LlmMessage:
    """Single chat-style message without provider transport details."""

    role: str
    content: str


@dataclass(frozen=True)
class LlmGenerationRequest:
    """Provider-neutral request for plain-text generation."""

    messages: tuple[LlmMessage, ...]
    model: str
    temperature: float | None = None
    max_output_tokens: int | None = None


@dataclass(frozen=True)
class TokenUsage:
    """Provider-neutral token accounting metadata."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class LlmGenerationResult:
    """Provider-neutral plain-text generation result."""

    text: str
    model: str
    finish_reason: str | None = None
    usage: TokenUsage | None = None


@dataclass(frozen=True)
class LlmStructuredGenerationRequest:
    """Provider-neutral request for schema-targeted generation."""

    messages: tuple[LlmMessage, ...]
    model: str
    schema_name: str
    temperature: float | None = None
    max_output_tokens: int | None = None


@dataclass(frozen=True)
class LlmStructuredGenerationResult:
    """Provider-neutral structured generation result."""

    payload: Any
    model: str
    finish_reason: str | None = None
    usage: TokenUsage | None = None


__all__ = [
    "LlmGenerationRequest",
    "LlmGenerationResult",
    "LlmMessage",
    "LlmStructuredGenerationRequest",
    "LlmStructuredGenerationResult",
    "TokenUsage",
]
