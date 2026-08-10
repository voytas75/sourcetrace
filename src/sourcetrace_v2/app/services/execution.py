from __future__ import annotations

import logging
import re
from dataclasses import dataclass, replace

from sourcetrace_v2.core.domain.identifiers import DegradationReason, FeatureId, StageId
from sourcetrace_v2.core.domain.models import (
    LlmExecutionReceipt,
    ResearchJob,
    ResearchResultArtifact,
    ResearchRun,
    RetrievedEvidenceCandidate,
)
from sourcetrace_v2.core.policies.deep_research import resolve_deep_research_stage_profile
from sourcetrace_v2.execution.context.models import ExecutionContext
from sourcetrace_v2.execution.receipts.collector import ReceiptCollector
from sourcetrace_v2.execution.stages.retrieval import RetrievalStage
from sourcetrace_v2.execution.stages.simple import SimpleLlmStage
from sourcetrace_v2.runtime.config.models import RuntimeConfig
from sourcetrace_v2.runtime.logging.context import LoggingContext
from sourcetrace_v2.runtime.logging.events import EventLogger


AUTHORITY_RELEVANCE_QUERY_HANDOFF_CONTRACT_V1 = "authority-relevance-query-handoff-contract-v1"
_WHITESPACE_RE = re.compile(r"\s+")
_QUERY_FOCUS_TOKEN_RE = re.compile(r"[a-z0-9]+")
_DOCUMENT_SOURCE_MARKERS = frozenset(
    {
        "article",
        "document",
        "paper",
        "pdf",
        "report",
        "study",
    }
)
_FINDINGS_INTENT_MARKERS = frozenset(
    {
        "conclusion",
        "conclusions",
        "finding",
        "findings",
        "result",
        "results",
        "summaries",
        "summarise",
        "summarize",
        "summary",
    }
)
_COMMUNITY_GROUP_MARKERS = frozenset(
    {
        "community",
        "communities",
        "diaspora",
        "expatriate",
        "expatriates",
        "immigrant",
        "immigrants",
        "migrant",
        "migrants",
        "migration",
        "refugee",
        "refugees",
    }
)
_QUALITY_OF_LIFE_MARKERS = frozenset(
    {
        "conditions",
        "life",
        "living",
        "qol",
        "wellbeing",
    }
)
_QUALITY_OF_LIFE_PHRASES = (
    "life satisfaction",
    "living conditions",
    "quality of life",
    "well being",
    "well-being",
)
_COMMUNITY_OUTCOME_FACETS = (
    "housing",
    "employment",
    "income",
    "health",
    "education",
    "discrimination",
    "integration",
    "life satisfaction",
)
_QUERY_FOCUS_STOPWORDS = frozenset(
    {
        "a",
        "about",
        "an",
        "and",
        "are",
        "as",
        "at",
        "by",
        "for",
        "how",
        "in",
        "is",
        "main",
        "major",
        "of",
        "on",
        "regarding",
        "the",
        "to",
        "what",
        "which",
    }
) | _DOCUMENT_SOURCE_MARKERS | _FINDINGS_INTENT_MARKERS


def _build_result_summary(
    *,
    seed_text: str,
    evidence_query: str,
    evidence_candidates: tuple[RetrievedEvidenceCandidate, ...],
) -> str:
    if evidence_candidates:
        top = evidence_candidates[0]
        return f"minimal v2 flow | query={evidence_query or seed_text} | top_source={top.provider}:{top.title}"
    return f"minimal v2 flow | query={evidence_query or seed_text} | top_source=none"


def _build_retrieval_query_handoff(*, seed_text: str) -> str:
    normalized = _WHITESPACE_RE.sub(" ", seed_text).strip()
    return normalized


@dataclass(frozen=True)
class QueryIntentProfile:
    normalized_seed: str
    facets: tuple[str, ...]
    focus_terms: tuple[str, ...]
    outcome_facets: tuple[str, ...]

    @property
    def prefers_document_sources(self) -> bool:
        return "document-like sources" in self.facets

    @property
    def asks_for_findings(self) -> bool:
        return "findings-oriented retrieval" in self.facets

    @property
    def prefers_community_outcome_retrieval(self) -> bool:
        return "community outcome-oriented retrieval" in self.facets


def _build_query_intent_profile(*, seed_text: str) -> QueryIntentProfile:
    normalized = _build_retrieval_query_handoff(seed_text=seed_text)
    tokens = tuple(_QUERY_FOCUS_TOKEN_RE.findall(normalized.lower()))
    token_set = set(tokens)
    facets: list[str] = []
    if token_set & _DOCUMENT_SOURCE_MARKERS:
        facets.append("document-like sources")
    if token_set & _FINDINGS_INTENT_MARKERS:
        facets.append("findings-oriented retrieval")
    outcome_facets: tuple[str, ...] = ()
    if _query_implies_community_outcome_focus(normalized):
        facets.append("community outcome-oriented retrieval")
        outcome_facets = _COMMUNITY_OUTCOME_FACETS
    return QueryIntentProfile(
        normalized_seed=normalized,
        facets=tuple(facets),
        focus_terms=_extract_query_focus_terms(normalized),
        outcome_facets=outcome_facets,
    )


def _extract_query_focus_terms(seed_text: str) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for token in _QUERY_FOCUS_TOKEN_RE.findall(seed_text.lower()):
        if token in _QUERY_FOCUS_STOPWORDS:
            continue
        if len(token) < 2:
            continue
        if token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return tuple(ordered)


def _build_query_refinement_prompt(*, seed_text: str) -> str:
    profile = _build_query_intent_profile(seed_text=seed_text)
    prompt = (
        "You are preparing a web retrieval query for an evidence-centric research system.\n"
        "Return exactly one search query line and nothing else.\n"
        "Keep the query bounded, faithful to user intent, and optimized for official/institutional evidence when relevant.\n"
        "Do not answer the question. Do not add commentary, bullets, prefixes, or quotes.\n"
    )
    if profile.facets:
        prompt += (
            "Derive the query from the user's concrete topic/entity terms rather than generic wrappers.\n"
            "Use document or publication terms only when they are already implied by the seed or needed to preserve the user's retrieval intent.\n"
            f"Intent facets: {', '.join(profile.facets)}\n"
        )
        if profile.focus_terms:
            prompt += f"Focus terms: {' '.join(profile.focus_terms)}\n"
        if profile.outcome_facets:
            prompt += (
                "Prefer direct outcome evidence over proxy themes when shaping the query.\n"
                f"Outcome facets: {' '.join(profile.outcome_facets)}\n"
        )
    return prompt + f"User seed: {profile.normalized_seed}"


def _build_planning_prompt(*, seed_text: str) -> str:
    profile = _build_query_intent_profile(seed_text=seed_text)
    lines = [
        "You are preparing a bounded research brief for downstream retrieval and evidence review.",
        "Do not answer the question.",
        "Return exactly three lines and nothing else.",
        "Line 1: focus: <8-16 words capturing the concrete research target>.",
        "Line 2: evidence: <3-6 short comma-separated evidence targets or outcome facets>.",
        "Line 3: cautions: <short scope or ambiguity note; write none if there is no caution>.",
        "Keep the total output under 60 words.",
        "Preserve named entities, geography, and requested source types when present.",
        "Prefer concrete evidence targets over broad framing.",
    ]
    if profile.prefers_document_sources:
        lines.append("Keep document/report emphasis because the seed asks for report-like evidence.")
    if profile.asks_for_findings:
        lines.append("Focus on findings/outcomes, not methodology or generic background.")
    if profile.prefers_community_outcome_retrieval and profile.outcome_facets:
        lines.append(f"Prioritize these outcome facets when relevant: {', '.join(profile.outcome_facets[:5])}.")
    if profile.focus_terms:
        lines.append(f"Focus terms: {', '.join(profile.focus_terms[:6])}.")
    lines.append(f"User seed: {profile.normalized_seed}")
    return "\n".join(lines)


def _query_implies_community_outcome_focus(seed_text: str) -> bool:
    lowered = seed_text.lower()
    tokens = set(_QUERY_FOCUS_TOKEN_RE.findall(lowered))
    community_like = bool(tokens & _COMMUNITY_GROUP_MARKERS)
    quality_of_life_like = bool(tokens & _QUALITY_OF_LIFE_MARKERS) or any(
        phrase in lowered for phrase in _QUALITY_OF_LIFE_PHRASES
    )
    return community_like and quality_of_life_like


def dataclass_replace_llm_receipt(
    receipt: LlmExecutionReceipt,
    degradation_reason: DegradationReason,
) -> LlmExecutionReceipt:
    return replace(receipt, degradation_reason=degradation_reason)


def _build_synthesis_prompt(
    *,
    seed_text: str,
    evidence_query: str,
    evidence_candidates: tuple[RetrievedEvidenceCandidate, ...],
) -> str:
    lines = [
        "You are writing a bounded evidence-grounded synthesis for an operator.",
        "Use only the evidence below. Do not ask the user to upload a PDF, paste text, or provide more material when evidence already exists.",
        "If PDF context is present, summarize the concrete PDF-derived findings first, then add limits/uncertainty.",
        "If the evidence is thin, say so briefly, but still give the best grounded synthesis you can from the available material.",
        "Prefer specific findings over generic workflow advice.",
        f"User question: {seed_text}",
        f"Retrieval query: {evidence_query or seed_text}",
        "Evidence:",
    ]
    for idx, candidate in enumerate(evidence_candidates[:3], start=1):
        lines.append(f"{idx}. title: {candidate.title}")
        lines.append(f"   url: {candidate.url}")
        if candidate.snippet:
            lines.append(f"   snippet: {candidate.snippet}")
        if candidate.pdf_context is not None:
            if candidate.pdf_context.document_scope:
                lines.append(f"   pdf_scope: {candidate.pdf_context.document_scope}")
            if candidate.pdf_context.entity_match_summary:
                lines.append(f"   pdf_entity: {candidate.pdf_context.entity_match_summary}")
            if candidate.pdf_context.key_findings:
                for finding in candidate.pdf_context.key_findings[:3]:
                    lines.append(f"   pdf_finding: {finding}")
    lines.extend([
        "Output requirements:",
        "- answer directly",
        "- cite the strongest evidence source titles inline in plain text",
        "- if a PDF was used, explicitly state the main PDF finding(s) you are relying on",
        "- avoid meta-commentary about missing uploads unless there is literally no usable evidence",
    ])
    return "\n".join(lines)


def _extract_refined_retrieval_query(*, seed_text: str, stage_output: str) -> tuple[str, DegradationReason | None]:
    fallback = _build_retrieval_query_handoff(seed_text=seed_text)
    normalized = _WHITESPACE_RE.sub(" ", stage_output).strip()
    if not normalized:
        return fallback, DegradationReason.VALIDATION_FALLBACK

    lines = [line.strip() for line in stage_output.splitlines() if line.strip()]
    candidate = _WHITESPACE_RE.sub(" ", lines[0] if lines else normalized).strip()
    lowered = candidate.lower()
    invalid_markers = (
        "this is",
        "here are",
        "if you want",
        "i can help",
        "summary",
        "answer:",
        "query:",
        "search query:",
        "stub:",
        "- ",
        "1.",
    )
    if any(marker in lowered for marker in invalid_markers):
        return fallback, DegradationReason.VALIDATION_FALLBACK
    if len(lines) > 1:
        return fallback, DegradationReason.VALIDATION_FALLBACK
    if len(candidate) < 8 or len(candidate) > 200:
        return fallback, DegradationReason.VALIDATION_FALLBACK
    return candidate, None


@dataclass(frozen=True)
class ExecutionOutcome:
    job: ResearchJob
    run: ResearchRun
    artifact: ResearchResultArtifact | None
    collector: ReceiptCollector


def execute_minimal_research_flow(*, job_id: str, run_id: str, seed_text: str, llm, search, config: RuntimeConfig, logger: logging.Logger | None = None, pdf=None) -> ExecutionOutcome:
    collector = ReceiptCollector()
    event_logger = EventLogger(logger or logging.getLogger("sourcetrace_v2.execution"))
    job = ResearchJob(job_id=job_id).mark_running()
    run = ResearchRun(run_id=run_id, job_id=job_id, feature=FeatureId.DEEP_RESEARCH)
    current_text = seed_text
    evidence_query = ""
    evidence_candidates = ()
    pretrim_evidence_candidates = ()
    retrieval_diagnostics = None
    retrieval_candidate_pool_count = 0
    retrieval_semantic_fit_status = "unknown"
    retrieval_best_focus_coverage = None
    retrieval_query = _build_retrieval_query_handoff(seed_text=seed_text)
    event_logger.info(
        "research flow started",
        context=LoggingContext(job_id=job_id, run_id=run_id, feature=FeatureId.DEEP_RESEARCH.value, event_name="job.started"),
    )
    try:
        for stage_id in (
            StageId.PLANNING,
            StageId.QUERY_REFINEMENT,
            StageId.RETRIEVAL,
            StageId.EVIDENCE_JUDGE,
            StageId.SYNTHESIS,
        ):
            call_site = f"minimal_flow.{stage_id}"
            event_logger.info(
                "stage started",
                context=LoggingContext(
                    job_id=job_id,
                    run_id=run_id,
                    feature=FeatureId.DEEP_RESEARCH.value,
                    stage_id=stage_id.value,
                    call_site=call_site,
                    event_name="stage.started",
                ),
            )
            if stage_id is StageId.RETRIEVAL:
                result = RetrievalStage(search=search, pdf=pdf).run(
                    context=ExecutionContext(
                        job_id=job_id,
                        run_id=run_id,
                        feature=FeatureId.DEEP_RESEARCH,
                        stage_id=stage_id,
                        call_site=call_site,
                    ),
                    collector=collector,
                    input_text=retrieval_query,
                )
                evidence_query = result.retrieval_query
                evidence_candidates = result.candidates
                pretrim_evidence_candidates = result.pretrim_candidates
                retrieval_diagnostics = result.retrieval_diagnostics
                retrieval_candidate_pool_count = result.candidate_pool_count
                retrieval_semantic_fit_status = result.semantic_fit_status
                retrieval_best_focus_coverage = result.best_focus_coverage
                current_text = current_text + "\n\nRetrieved evidence candidates:\n" + "\n".join(
                    f"- [{candidate.rank}] {candidate.title} <{candidate.url}>" for candidate in result.candidates
                )
            else:
                profile_name = resolve_deep_research_stage_profile(policy=config.deep_research, stage_id=stage_id)
                stage = SimpleLlmStage(profile_name=profile_name, llm=llm)
                stage_input = (
                    _build_planning_prompt(seed_text=seed_text)
                    if stage_id is StageId.PLANNING
                    else _build_query_refinement_prompt(seed_text=seed_text)
                    if stage_id is StageId.QUERY_REFINEMENT
                    else _build_synthesis_prompt(
                        seed_text=seed_text,
                        evidence_query=evidence_query,
                        evidence_candidates=evidence_candidates,
                    )
                    if stage_id is StageId.SYNTHESIS
                    else current_text
                )
                result = stage.run(
                    context=ExecutionContext(
                        job_id=job_id,
                        run_id=run_id,
                        feature=FeatureId.DEEP_RESEARCH,
                        stage_id=stage_id,
                        call_site=call_site,
                    ),
                    collector=collector,
                    input_text=stage_input,
                )
                if stage_id is StageId.QUERY_REFINEMENT:
                    retrieval_query, degradation_reason = _extract_refined_retrieval_query(
                        seed_text=seed_text,
                        stage_output=result.output_text,
                    )
                    if degradation_reason is not None and collector.llm_receipts:
                        collector.llm_receipts[-1] = dataclass_replace_llm_receipt(collector.llm_receipts[-1], degradation_reason)
                    current_text = current_text + f"\n\nRetrieval query:\n{retrieval_query}"
                else:
                    current_text = result.output_text
            stage_receipt = collector.stage_receipts[-1]
            log_method = event_logger.warning if stage_receipt.status.value == "degraded" else event_logger.info
            log_method(
                "stage finished",
                context=LoggingContext(
                    job_id=job_id,
                    run_id=run_id,
                    feature=FeatureId.DEEP_RESEARCH.value,
                    stage_id=stage_id.value,
                    call_site=call_site,
                    event_name="stage.finished",
                ),
            )
    except Exception:
        event_logger.error(
            "research flow failed",
            context=LoggingContext(job_id=job_id, run_id=run_id, feature=FeatureId.DEEP_RESEARCH.value, event_name="job.failed"),
        )
        return ExecutionOutcome(
            job=job.mark_error(),
            run=run,
            artifact=None,
            collector=collector,
        )
    artifact = ResearchResultArtifact(
        job_id=job_id,
        run_id=run_id,
        result_text=current_text,
        summary=_build_result_summary(
            seed_text=seed_text,
            evidence_query=evidence_query,
            evidence_candidates=evidence_candidates,
        ),
        evidence_query=evidence_query,
        evidence_candidates=evidence_candidates,
        pretrim_evidence_candidates=pretrim_evidence_candidates,
        retrieval_diagnostics=retrieval_diagnostics,
        retrieval_candidate_pool_count=retrieval_candidate_pool_count,
        retrieval_semantic_fit_status=retrieval_semantic_fit_status,
        retrieval_best_focus_coverage=retrieval_best_focus_coverage,
    )
    done_job = job.mark_done()
    event_logger.info(
        "research flow completed",
        context=LoggingContext(job_id=job_id, run_id=run_id, feature=FeatureId.DEEP_RESEARCH.value, event_name="job.completed"),
    )
    return ExecutionOutcome(
        job=done_job,
        run=run,
        artifact=artifact,
        collector=collector,
    )
