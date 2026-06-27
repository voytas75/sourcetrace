from __future__ import annotations

import logging

from sourcetrace_v2.core.contracts.persistence import ReceiptRepository, ResultArtifactRepository
from sourcetrace_v2.core.contracts.read_models import PersistedExecutionView
from sourcetrace_v2.app.services.execution import execute_minimal_research_flow
from sourcetrace_v2.app.services.persistence import persist_execution_outcome
from sourcetrace_v2.app.services.readback import load_persisted_execution_view
from sourcetrace_v2.runtime.config.models import RuntimeConfig


def run_and_persist_minimal_flow(*, job_id: str, run_id: str, seed_text: str, llm, results: ResultArtifactRepository, receipts: ReceiptRepository, config: RuntimeConfig, logger: logging.Logger | None = None) -> PersistedExecutionView:
    outcome = execute_minimal_research_flow(
        job_id=job_id,
        run_id=run_id,
        seed_text=seed_text,
        llm=llm,
        config=config,
        logger=logger,
    )
    persist_execution_outcome(outcome=outcome, results=results, receipts=receipts)
    return load_persisted_execution_view(
        job_id=outcome.job.job_id,
        run_id=outcome.run.run_id,
        results=results,
        receipts=receipts,
    )
