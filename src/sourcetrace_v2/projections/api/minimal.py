from __future__ import annotations

from sourcetrace_v2.core.domain.models import ResearchJob, ResearchResultArtifact, ResearchRun
from sourcetrace_v2.execution.receipts.collector import ReceiptCollector


def project_minimal_result(*, job: ResearchJob, run: ResearchRun, artifact: ResearchResultArtifact, collector: ReceiptCollector) -> dict[str, object]:
    rollup = collector.build_rollup(job_id=job.job_id, run_id=run.run_id)
    return {
        "job": {
            "job_id": job.job_id,
            "status": job.status.value,
            "feature": job.feature.value,
        },
        "run": {
            "run_id": run.run_id,
            "feature": run.feature.value,
        },
        "result": {
            "summary": artifact.summary,
            "text": artifact.result_text,
        },
        "evidence_input": {
            "query": artifact.evidence_query,
            "candidate_count": len(artifact.evidence_candidates),
            "candidates": [
                {
                    "title": candidate.title,
                    "url": candidate.url,
                    "provider": candidate.provider,
                    "rank": candidate.rank,
                }
                for candidate in artifact.evidence_candidates
            ],
        },
        "rollup": {
            "llm_calls": rollup.llm_calls,
            "input_tokens": rollup.input_tokens,
            "output_tokens": rollup.output_tokens,
            "total_tokens": rollup.total_tokens,
            "degraded_calls": rollup.degraded_calls,
            "failed_stages": rollup.failed_stages,
        },
        "receipts": {
            "stages": len(collector.stage_receipts),
            "llm": len(collector.llm_receipts),
        },
    }
