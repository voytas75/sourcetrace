from sourcetrace.llm.extraction import build_claim_extraction_gateway
from sourcetrace.llm.interfaces import StructuredGenerationRuntime
from sourcetrace.llm.models import LlmStructuredGenerationResult


class _Recorder:
    def __init__(self) -> None:
        self.task_name = None
        self.schema_name = None
        self.messages = None

    def __call__(self, *, task_name: str, schema_name: str, messages):
        self.task_name = task_name
        self.schema_name = schema_name
        self.messages = messages
        return LlmStructuredGenerationResult(payload={"claims": []}, model="gpt-test")


def test_claim_extraction_gateway_explicitly_requests_json_output_in_prompt() -> None:
    recorder = _Recorder()
    gateway = build_claim_extraction_gateway(
        execution=StructuredGenerationRuntime(generate_structured=recorder)
    )

    gateway("Prepared text paragraph.")

    assert recorder.task_name == "claim_extraction"
    assert recorder.schema_name == "ClaimExtractionPayload"
    assert recorder.messages is not None
    assert len(recorder.messages) == 1
    prompt = recorder.messages[0].content.lower()
    assert "json" in prompt
    assert "claim" in prompt
    assert "prepared text paragraph." in prompt


def test_claim_extraction_gateway_explicitly_forbids_conversational_or_question_outputs() -> None:
    recorder = _Recorder()
    gateway = build_claim_extraction_gateway(
        execution=StructuredGenerationRuntime(generate_structured=recorder)
    )

    gateway("The network expanded in 2025.")

    assert recorder.messages is not None
    prompt = recorder.messages[0].content.lower()
    assert "do not ask follow-up questions" in prompt
    assert "do not ask for clarification" in prompt
    assert "assistant replies" in prompt
    assert "summaries" in prompt
    assert "explanations" in prompt
    assert "exact text from the source" in prompt


def test_claim_extraction_gateway_requires_single_raw_json_object_without_wrappers() -> None:
    recorder = _Recorder()
    gateway = build_claim_extraction_gateway(
        execution=StructuredGenerationRuntime(generate_structured=recorder)
    )

    gateway("Inflation rose in April.")

    assert recorder.messages is not None
    prompt = recorder.messages[0].content.lower()
    assert "return only one valid json object" in prompt
    assert "do not wrap the json in markdown or code fences" in prompt
    assert "do not include any text before or after the json object" in prompt
    assert 'return {"claims": []}' in prompt


def test_claim_extraction_gateway_instructs_preservation_of_attribution_when_it_owns_the_claim() -> None:
    recorder = _Recorder()
    gateway = build_claim_extraction_gateway(
        execution=StructuredGenerationRuntime(generate_structured=recorder)
    )

    gateway(
        "According to the central bank, inflation fell to 3.1 percent in April, but the agency warned the figure may be revised."
    )

    assert recorder.messages is not None
    prompt = recorder.messages[0].content.lower()
    assert "according to" in prompt
    assert "x said" in prompt
    assert "named institution" in prompt or "institution" in prompt
    assert "preserve attribution" in prompt
    assert "keep attribution-bearing wording" in prompt
    assert "do not rewrite attributed claims into unattributed propositions" in prompt
    assert "do not emit a separate attribution-only claim" in prompt


def test_claim_extraction_gateway_requires_contrastive_sentences_to_yield_at_least_one_claim() -> None:
    recorder = _Recorder()
    gateway = build_claim_extraction_gateway(
        execution=StructuredGenerationRuntime(generate_structured=recorder)
    )

    gateway(
        "Although the bridge reopened to cars on Tuesday, heavy trucks remain barred until next week."
    )

    assert recorder.messages is not None
    prompt = recorder.messages[0].content.lower()
    assert "do not return {\"claims\": []} when the source contains a clear factual clause" in prompt
    assert "contrastive sentences still contain extractable claims" in prompt
    assert "although the bridge reopened to cars on tuesday" in prompt
    assert "heavy trucks remain barred until next week" in prompt


def test_claim_extraction_gateway_instructs_grouping_of_linked_analytical_subclauses() -> None:
    recorder = _Recorder()
    gateway = build_claim_extraction_gateway(
        execution=StructuredGenerationRuntime(generate_structured=recorder)
    )

    gateway(
        "The strike reportedly knocked out 17% of global LNG supply and may cost QatarEnergy about $20bn in annual revenues, with repairs taking 3 to 5 years."
    )

    assert recorder.messages is not None
    prompt = recorder.messages[0].content.lower()
    assert "prefer one grouped claim" in prompt
    assert "single analytical proposition" in prompt or "single analytical claim" in prompt
    assert "do not split short dependent fragments" in prompt
    assert "repairs taking 3 to 5 years" in prompt
