"""Temporary demo helper.

This module is intentionally non-canonical.
Prefer the v2 canonical path:
- RuntimeAssembly
- run_and_persist_minimal_flow(...)
- load_persisted_execution_view(...)
- handle_run_minimal_flow_request(...)
- handle_get_persisted_execution_request(...)
"""

from __future__ import annotations

from sourcetrace_v2.adapters.storage.memory import InMemoryReceiptRepository, InMemoryResultArtifactRepository
from sourcetrace_v2.adapters.llm.stub import StubLlmGateway
from sourcetrace_v2.app.services.run_use_case import run_and_persist_minimal_flow
from sourcetrace_v2.runtime.config.defaults import build_default_runtime_config


def run_persisted_minimal_flow(*, job_id: str, run_id: str, seed_text: str) -> dict[str, object]:
    config = build_default_runtime_config()
    view = run_and_persist_minimal_flow(
        job_id=job_id,
        run_id=run_id,
        seed_text=seed_text,
        llm=StubLlmGateway(config),
        results=InMemoryResultArtifactRepository(),
        receipts=InMemoryReceiptRepository(),
        config=config,
    )
    return {
        "status": view.status.value,
        "job_id": view.rollup.job_id,
        "run_id": view.rollup.run_id,
        "job_status": "done",
        "artifact_text": view.artifact.result_text if view.artifact is not None else None,
        "llm_calls": view.rollup.llm_calls,
        "total_tokens": view.rollup.total_tokens,
        "degraded_calls": view.rollup.degraded_calls,
        "failed_stages": view.rollup.failed_stages,
        "stage_receipts": len(view.stage_receipts),
        "llm_receipts": len(view.llm_receipts),
    }
