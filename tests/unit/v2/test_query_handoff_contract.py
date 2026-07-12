from __future__ import annotations

from sourcetrace_v2.adapters.llm.interfaces import LlmCallResult, LlmTextGateway
from sourcetrace_v2.adapters.search.interfaces import SearchGateway
from sourcetrace_v2.app.services.execution import (
    AUTHORITY_RELEVANCE_QUERY_HANDOFF_CONTRACT_V1,
    _build_planning_prompt,
    _build_query_intent_profile,
    _build_query_refinement_prompt,
    execute_minimal_research_flow,
)
from sourcetrace_v2.core.domain.models import RetrievedEvidenceCandidate
from sourcetrace_v2.runtime.config.defaults import build_default_runtime_config
from sourcetrace_v2.runtime.logging.setup import configure_logging


class ProseRefinementGateway(LlmTextGateway):
    def generate(self, *, profile_name: str, prompt: str) -> LlmCallResult:
        return LlmCallResult(
            text=f"This is a solid summary of the answer for {prompt}. If you want, I can help turn it into a final response.",
            provider="test-provider",
            model="test-model",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            finish_reason="stop",
        )


class QueryRefinementGateway(LlmTextGateway):
    def __init__(self) -> None:
        self.prompts: list[tuple[str, str]] = []

    def generate(self, *, profile_name: str, prompt: str) -> LlmCallResult:
        self.prompts.append((profile_name, prompt))
        if profile_name == "research_fast":
            return LlmCallResult(
                text="official faq remote work reporting obligations employers poland labour ministry",
                provider="test-provider",
                model="test-model",
                input_tokens=10,
                output_tokens=8,
                total_tokens=18,
                finish_reason="stop",
            )
        return LlmCallResult(
            text="final synthesis output",
            provider="test-provider",
            model="test-model",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            finish_reason="stop",
        )


class RecordingSearchGateway(SearchGateway):
    def __init__(self) -> None:
        self.queries: list[str] = []

    def search(self, *, job_id: str, run_id: str, query: str, limit: int) -> tuple[RetrievedEvidenceCandidate, ...]:
        self.queries.append(query)
        return tuple(
            RetrievedEvidenceCandidate(
                candidate_id=f"cand:{run_id}:{index}",
                job_id=job_id,
                run_id=run_id,
                provider="recording-search",
                query=query,
                title=f"Result {index + 1}",
                url=f"https://example.test/{index + 1}",
                snippet=f"Snippet for {query}",
                rank=index + 1,
            )
            for index in range(limit)
        )


def test_minimal_flow_uses_valid_llm_refined_query_for_retrieval() -> None:
    config = build_default_runtime_config()
    logger = configure_logging(config.logging)
    search = RecordingSearchGateway()
    llm = QueryRefinementGateway()

    outcome = execute_minimal_research_flow(
        job_id="job-query-handoff",
        run_id="run-query-handoff",
        seed_text=" remote work reporting obligations Poland employer official guidance ",
        llm=llm,
        search=search,
        config=config,
        logger=logger,
    )

    assert AUTHORITY_RELEVANCE_QUERY_HANDOFF_CONTRACT_V1 == "authority-relevance-query-handoff-contract-v1"
    assert search.queries == ["official faq remote work reporting obligations employers poland labour ministry"]
    assert outcome.artifact is not None
    assert outcome.artifact.evidence_query == "official faq remote work reporting obligations employers poland labour ministry"
    assert outcome.artifact.evidence_candidates[0].query == "official faq remote work reporting obligations employers poland labour ministry"
    assert llm.prompts[0][0] == "planning_default"
    assert "Return exactly three lines and nothing else." in llm.prompts[0][1]
    assert llm.prompts[0][1] != " remote work reporting obligations Poland employer official guidance "
    assert llm.prompts[1][0] == "research_fast"
    assert "Return exactly one search query line" in llm.prompts[1][1]


def test_minimal_flow_falls_back_to_seed_when_query_refinement_returns_prose() -> None:
    config = build_default_runtime_config()
    logger = configure_logging(config.logging)
    search = RecordingSearchGateway()

    outcome = execute_minimal_research_flow(
        job_id="job-query-handoff-fallback",
        run_id="run-query-handoff-fallback",
        seed_text=" break glass\n account guidance   conditional access official best practice ",
        llm=ProseRefinementGateway(),
        search=search,
        config=config,
        logger=logger,
    )

    assert search.queries == ["break glass account guidance conditional access official best practice"]
    assert outcome.artifact is not None
    assert outcome.artifact.evidence_query == "break glass account guidance conditional access official best practice"
    assert outcome.artifact.evidence_candidates[0].query == "break glass account guidance conditional access official best practice"
    assert "This is a solid summary" not in outcome.artifact.evidence_query
    assert outcome.collector.llm_receipts[1].degradation_reason is not None


def test_query_refinement_prompt_adds_topical_focus_hint_for_pdf_findings_questions() -> None:
    profile = _build_query_intent_profile(
        seed_text="What are the main findings in the PDF document about hybrid remote work in Poland?",
    )
    prompt = _build_query_refinement_prompt(
        seed_text="What are the main findings in the PDF document about hybrid remote work in Poland?",
    )

    assert profile.prefers_document_sources is True
    assert profile.asks_for_findings is True
    assert profile.focus_terms == ("hybrid", "remote", "work", "poland")
    assert "Derive the query from the user's concrete topic/entity terms rather than generic wrappers." in prompt
    assert "Intent facets: document-like sources, findings-oriented retrieval" in prompt
    assert "Focus terms: hybrid remote work poland" in prompt


def test_planning_prompt_adds_bounded_contract_and_outcome_hints_for_diaspora_query() -> None:
    seed_text = "What are the main findings in PDF reports about the quality of life of the Polish diaspora in Germany?"
    prompt = _build_planning_prompt(seed_text=seed_text)

    assert "Return exactly three lines and nothing else." in prompt
    assert "Keep the total output under 60 words." in prompt
    assert "Keep document/report emphasis because the seed asks for report-like evidence." in prompt
    assert "Focus on findings/outcomes, not methodology or generic background." in prompt
    assert "Prioritize these outcome facets when relevant: housing, employment, income, health, education." in prompt
    assert "Focus terms: polish, germany." not in prompt
    assert "Focus terms: reports, quality, life, polish, diaspora, germany." in prompt
    assert prompt.endswith(f"User seed: {seed_text}")


def test_query_refinement_prompt_adds_outcome_facet_hint_for_community_quality_of_life_queries() -> None:
    seed_text = "What are the main findings in PDF reports about the quality of life of the Polish diaspora in Germany?"
    profile = _build_query_intent_profile(seed_text=seed_text)
    prompt = _build_query_refinement_prompt(seed_text=seed_text)

    assert profile.prefers_document_sources is True
    assert profile.asks_for_findings is True
    assert profile.prefers_community_outcome_retrieval is True
    assert profile.outcome_facets == (
        "housing",
        "employment",
        "income",
        "health",
        "education",
        "discrimination",
        "integration",
        "life satisfaction",
    )
    assert "Intent facets: document-like sources, findings-oriented retrieval, community outcome-oriented retrieval" in prompt
    assert "Prefer direct outcome evidence over proxy themes when shaping the query." in prompt
    assert "Outcome facets: housing employment income health education discrimination integration life satisfaction" in prompt


def test_query_refinement_prompt_keeps_general_queries_free_of_pdf_focus_hint() -> None:
    prompt = _build_query_refinement_prompt(
        seed_text="remote work reporting obligations Poland employer official guidance",
    )

    assert "Intent facets:" not in prompt
    assert "Focus terms:" not in prompt
    assert "Derive the query from the user's concrete topic/entity terms rather than generic wrappers." not in prompt
