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
