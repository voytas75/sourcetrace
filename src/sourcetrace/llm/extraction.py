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
                        "For sentences with while, despite, although, though, however, or but, "
                        "where the secondary clause is attribution, caveat, or context such as "
                        "X said, analysts saying, or according to, return the main factual "
                        "proposition as the claim. "
                        "Do not emit a separate attribution-only claim. "
                        "If a sentence contains a main proposition plus attributed caveat or "
                        "context, prefer one claim for the main proposition using source wording "
                        "when possible. "
                        "Contrastive sentences still contain extractable claims when at least one "
                        "clause states a concrete factual proposition. "
                        "Do not return {\"claims\": []} when the source contains a clear "
                        "factual clause such as 'Although the bridge reopened to cars on Tuesday, "
                        "heavy trucks remain barred until next week.' Prefer the concrete factual "
                        "clause with the clearest standalone proposition, such as 'heavy trucks "
                        "remain barred until next week.' "
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
