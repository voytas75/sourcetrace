"""Thin structured-generation helper layer over provider-neutral seams."""

from dataclasses import dataclass

from sourcetrace.llm.config import SourceTraceLlmConfig
from sourcetrace.llm.errors import LlmSchemaError
from sourcetrace.llm.interfaces import StructuredLlmGenerationExecution, StructuredLlmGenerator
from sourcetrace.llm.models import (
    LlmMessage,
    LlmStructuredGenerationRequest,
    LlmStructuredGenerationResult,
)


class _StructuredGenerationCallable:
    def __init__(
        self,
        *,
        generate_structured: StructuredLlmGenerator,
        config: SourceTraceLlmConfig,
    ) -> None:
        self._generate_structured = generate_structured
        self._config = config

    def __call__(
        self,
        *,
        task_name: str,
        schema_name: str,
        messages: tuple[LlmMessage, ...],
    ) -> LlmStructuredGenerationResult:
        task = self._config.task(task_name)
        result = self._generate_structured(
            LlmStructuredGenerationRequest(
                messages=messages,
                model=task.model,
                schema_name=schema_name,
                temperature=task.temperature,
                max_output_tokens=task.max_output_tokens,
            )
        )
        if not isinstance(result.payload, dict):
            raise LlmSchemaError(f"structured payload for {schema_name} must be a mapping")
        return result


def build_structured_generation_execution(
    *,
    generate_structured: StructuredLlmGenerator,
    config: SourceTraceLlmConfig,
) -> StructuredLlmGenerationExecution:
    """Bind task routing config to the structured generation seam."""

    return StructuredLlmGenerationExecution(
        generate_structured=_StructuredGenerationCallable(
            generate_structured=generate_structured,
            config=config,
        )
    )


__all__ = ["build_structured_generation_execution"]
