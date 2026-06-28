from __future__ import annotations

import logging
import re
from dataclasses import dataclass, replace

from sourcetrace_v2.core.domain.identifiers import DegradationReason, FeatureId, StageId
from sourcetrace_v2.core.domain.models import ResearchJob, ResearchResultArtifact, ResearchRun
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


def _build_result_summary(*, seed_text: str, evidence_query: str, evidence_candidates: tuple) -> str:
    if evidence_candidates:
        top = evidence_candidates[0]
        return f"minimal v2 flow | query={evidence_query or seed_text} | top_source={top.provider}:{top.title}"
    return f"minimal v2 flow | query={evidence_query or seed_text} | top_source=none"


def _build_retrieval_query_handoff(*, seed_text: str) -> str:
    normalized = _WHITESPACE_RE.sub(" ", seed_text).strip()
    return normalized


def _build_query_refinement_prompt(*, seed_text: str) -> str:
    normalized = _build_retrieval_query_handoff(seed_text=seed_text)
    return (
        "You are preparing a web retrieval query for an evidence-centric research system.\n"
        "Return exactly one search query line and nothing else.\n"
        "Keep the query bounded, faithful to user intent, and optimized for official/institutional evidence when relevant.\n"
        "Do not answer the question. Do not add commentary, bullets, prefixes, or quotes.\n"
        f"User seed: {normalized}"
    )


def dataclass_replace_llm_receipt(receipt, degradation_reason: DegradationReason):
    return replace(receipt, degradation_reason=degradation_reason)


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
                current_text = current_text + "\n\nRetrieved evidence candidates:\n" + "\n".join(
                    f"- [{candidate.rank}] {candidate.title} <{candidate.url}>" for candidate in result.candidates
                )
            else:
                profile_name = resolve_deep_research_stage_profile(policy=config.deep_research, stage_id=stage_id)
                stage = SimpleLlmStage(profile_name=profile_name, llm=llm)
                stage_input = (
                    _build_query_refinement_prompt(seed_text=seed_text)
                    if stage_id is StageId.QUERY_REFINEMENT
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
