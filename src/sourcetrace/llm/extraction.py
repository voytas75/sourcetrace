"""Task-specific claim extraction gateway over structured generation."""

from sourcetrace.llm.interfaces import ClaimExtractionGateway, StructuredGenerationRuntime
from sourcetrace.llm.models import LlmMessage, LlmStructuredGenerationResult


class _ClaimExtractionGateway:
    def __init__(self, *, execution: StructuredGenerationRuntime) -> None:
        self._execution = execution

    def __call__(self, prepared_text: str) -> LlmStructuredGenerationResult:
        return self._execution.generate_structured(
            task_name="claim_extraction",
            schema_name="ClaimExtractionPayload",
            messages=(
                LlmMessage(
                    role="user",
                    content=(
                        "Extract structured claims from the prepared source text. "
                        "Return valid JSON that matches the ClaimExtractionPayload schema. "
                        "Return only one valid JSON object. "
                        "Do not wrap the JSON in markdown or code fences. "
                        "Do not include any text before or after the JSON object. "
                        "If no claims are found, return {\"claims\": []}. "
                        "Output only factual claim candidates grounded in the source text. "
                        "Use exact text from the source when possible. "
                        "Do not ask follow-up questions. "
                        "Do not ask for clarification. "
                        "Do not write assistant replies, summaries, explanations, or advice.\n\n"
                        f"{prepared_text}"
                    ),
                ),
            ),
        )


def build_claim_extraction_gateway(
    *,
    execution: StructuredGenerationRuntime,
) -> ClaimExtractionGateway:
    """Create the first task-specific extraction gateway."""

    return _ClaimExtractionGateway(execution=execution)


__all__ = ["build_claim_extraction_gateway"]
