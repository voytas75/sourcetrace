from __future__ import annotations

import logging

from sourcetrace_v2.adapters.llm.interfaces import LlmTextGateway
from sourcetrace_v2.adapters.pdf.interfaces import PdfReadGateway
from sourcetrace_v2.adapters.search.interfaces import SearchGateway
from sourcetrace_v2.core.contracts.persistence import ReceiptRepository, ResultArtifactRepository
from sourcetrace_v2.core.contracts.read_models import PersistedExecutionView, PersistedViewStatus
from sourcetrace_v2.app.services.execution import execute_minimal_research_flow
from sourcetrace_v2.app.services.persistence import persist_execution_outcome
from sourcetrace_v2.app.services.readback import load_persisted_execution_view
from sourcetrace_v2.runtime.config.models import RuntimeConfig


class RunIdentityConflictError(Exception):
    pass


def run_and_persist_minimal_flow(*, job_id: str, run_id: str, seed_text: str, llm: LlmTextGateway, search: SearchGateway, results: ResultArtifactRepository, receipts: ReceiptRepository, config: RuntimeConfig, logger: logging.Logger | None = None, pdf: PdfReadGateway | None = None) -> PersistedExecutionView:
    existing = load_persisted_execution_view(
        job_id=job_id,
        run_id=run_id,
        results=results,
        receipts=receipts,
    )
    if existing.status is not PersistedViewStatus.NOT_FOUND:
        raise RunIdentityConflictError(f"run identity already exists: {job_id}/{run_id}")
    outcome = execute_minimal_research_flow(
        job_id=job_id,
        run_id=run_id,
        seed_text=seed_text,
        llm=llm,
        search=search,
        config=config,
        logger=logger,
        pdf=pdf,
    )
    persist_execution_outcome(outcome=outcome, results=results, receipts=receipts)
    return load_persisted_execution_view(
        job_id=outcome.job.job_id,
        run_id=outcome.run.run_id,
        results=results,
        receipts=receipts,
    )
