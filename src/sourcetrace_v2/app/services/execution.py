from __future__ import annotations

import logging
from dataclasses import dataclass

from sourcetrace_v2.core.domain.identifiers import FeatureId, StageId
from sourcetrace_v2.core.domain.models import ResearchJob, ResearchResultArtifact, ResearchRun
from sourcetrace_v2.core.policies.deep_research import resolve_deep_research_stage_profile
from sourcetrace_v2.execution.context.models import ExecutionContext
from sourcetrace_v2.execution.receipts.collector import ReceiptCollector
from sourcetrace_v2.execution.stages.simple import SimpleLlmStage
from sourcetrace_v2.runtime.config.models import RuntimeConfig
from sourcetrace_v2.runtime.logging.context import LoggingContext
from sourcetrace_v2.runtime.logging.events import EventLogger


@dataclass(frozen=True)
class ExecutionOutcome:
    job: ResearchJob
    run: ResearchRun
    artifact: ResearchResultArtifact | None
    collector: ReceiptCollector


def execute_minimal_research_flow(*, job_id: str, run_id: str, seed_text: str, llm, config: RuntimeConfig, logger: logging.Logger | None = None) -> ExecutionOutcome:
    collector = ReceiptCollector()
    event_logger = EventLogger(logger or logging.getLogger("sourcetrace_v2.execution"))
    job = ResearchJob(job_id=job_id).mark_running()
    run = ResearchRun(run_id=run_id, job_id=job_id, feature=FeatureId.DEEP_RESEARCH)
    current_text = seed_text
    event_logger.info(
        "research flow started",
        context=LoggingContext(job_id=job_id, run_id=run_id, feature=FeatureId.DEEP_RESEARCH.value, event_name="job.started"),
    )
    try:
        for stage_id in (
            StageId.PLANNING,
            StageId.QUERY_REFINEMENT,
            StageId.EVIDENCE_JUDGE,
            StageId.SYNTHESIS,
        ):
            profile_name = resolve_deep_research_stage_profile(policy=config.deep_research, stage_id=stage_id)
            stage = SimpleLlmStage(profile_name=profile_name, llm=llm)
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
            result = stage.run(
                context=ExecutionContext(
                    job_id=job_id,
                    run_id=run_id,
                    feature=FeatureId.DEEP_RESEARCH,
                    stage_id=stage_id,
                    call_site=call_site,
                ),
                collector=collector,
                input_text=current_text,
            )
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
            current_text = result.output_text
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
    artifact = ResearchResultArtifact(job_id=job_id, run_id=run_id, result_text=current_text, summary="minimal v2 flow")
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
