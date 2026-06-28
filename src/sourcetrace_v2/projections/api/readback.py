from __future__ import annotations

from sourcetrace_v2.core.contracts.read_models import PersistedExecutionView
from sourcetrace_v2.projections.api.compiled_artifacts import project_compiled_artifact
from sourcetrace_v2.projections.api.evidence import project_selected_evidence


def project_persisted_execution_view(*, view: PersistedExecutionView) -> dict[str, object]:
    artifact = view.artifact
    envelope = view.envelope
    return {
        "status": view.status.value,
        "job_id": envelope.job_id,
        "run_id": envelope.run_id,
        "persistence": {
            "completeness": envelope.persistence_completeness.value,
            "artifact_present": envelope.artifact_present,
            "marker_present": envelope.marker_present,
            "marker_state": envelope.marker_state,
        },
        "artifact": {
            "present": artifact is not None,
            "summary": artifact.summary if artifact is not None else None,
            "text": artifact.result_text if artifact is not None else None,
        },
        "compiled_artifact": project_compiled_artifact(
            artifact=view.compiled_artifact if hasattr(view, "compiled_artifact") else None
        ),
        "evidence_input": {
            "query": artifact.evidence_query if artifact is not None else "",
            "candidate_count": len(artifact.evidence_candidates) if artifact is not None else 0,
            "candidates": [
                {
                    "title": candidate.title,
                    "url": candidate.url,
                    "provider": candidate.provider,
                    "rank": candidate.rank,
                    "source_type": candidate.source_type,
                }
                for candidate in (artifact.evidence_candidates if artifact is not None else ())
            ],
        },
        "selected_evidence": project_selected_evidence(artifact=artifact),
        "rollup": {
            "llm_calls": view.rollup.llm_calls,
            "input_tokens": view.rollup.input_tokens,
            "output_tokens": view.rollup.output_tokens,
            "total_tokens": view.rollup.total_tokens,
            "degraded_calls": view.rollup.degraded_calls,
            "failed_stages": view.rollup.failed_stages,
        },
        "receipts": {
            "stage_count": len(view.stage_receipts),
            "llm_count": len(view.llm_receipts),
            "stages": [
                {
                    "receipt_id": receipt.receipt_id,
                    "stage_id": receipt.stage_id.value,
                    "status": receipt.status.value,
                    "call_site": receipt.call_site,
                    "degradation_reason": receipt.degradation_reason.value if receipt.degradation_reason is not None else None,
                }
                for receipt in view.stage_receipts
            ],
            "llm": [
                {
                    "receipt_id": receipt.receipt_id,
                    "stage_id": receipt.stage_id.value,
                    "profile": receipt.profile,
                    "provider": receipt.provider,
                    "model": receipt.model,
                    "coverage_status": receipt.coverage_status.value,
                    "total_tokens": receipt.total_tokens,
                    "finish_reason": receipt.finish_reason,
                    "degradation_reason": receipt.degradation_reason.value if receipt.degradation_reason is not None else None,
                }
                for receipt in view.llm_receipts
            ],
        },
    }
