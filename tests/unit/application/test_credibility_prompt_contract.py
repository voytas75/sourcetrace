from sourcetrace.application.credibility_runtime import build_llm_credibility_assessor
from sourcetrace.application.credibility import CredibilityAssessmentRequest
from sourcetrace.domain import Document
from sourcetrace.llm.models import LlmGenerationResult
from datetime import UTC, datetime


class _Recorder:
    def __init__(self) -> None:
        self.prompt = None

    def __call__(self, evidence_summary: str) -> LlmGenerationResult:
        self.prompt = evidence_summary
        return LlmGenerationResult(text='{"summary":"x","strengths":[],"concerns":[],"verification_checks":[],"source_reliability":"unknown","information_credibility":"unknown","source_reliability_factors":[],"information_credibility_factors":[],"provenance_distance":"unknown"}', model='gpt-test', finish_reason='stop')


def test_credibility_prompt_requires_typed_assessment_fields_and_unknown_fallback() -> None:
    recorder = _Recorder()
    assessor = build_llm_credibility_assessor(
        draft_credibility=recorder,
        assessed_at=lambda: datetime(2026, 5, 24, 12, 0, tzinfo=UTC),
    )
    document = Document(
        document_id='doc-1',
        case_id='case-1',
        source_type='url',
        source_url='https://example.test/report',
        publisher='Example News',
        author='Analyst',
        title='Network report',
        published_at=datetime(2026, 5, 18, 0, 0, tzinfo=UTC),
        retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
        content_hash='sha256:abc123',
        language='en',
    )

    assessor(CredibilityAssessmentRequest(document=document, assessment_method='llm_draft_v1'))

    assert recorder.prompt is not None
    prompt = recorder.prompt.lower()
    assert 'respond as concise json only' in prompt
    assert 'required top-level keys' in prompt
    assert 'source_reliability' in prompt
    assert 'information_credibility' in prompt
    assert 'provenance_distance' in prompt
    assert 'explicitly return unknown instead of guessing' in prompt
    assert 'keep strengths/concerns/factor fields as short string arrays' in prompt
