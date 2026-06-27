from __future__ import annotations

from sourcetrace_v2.adapters.llm.stub import StubLlmGateway
from sourcetrace_v2.adapters.storage.memory import InMemoryReceiptRepository, InMemoryResultArtifactRepository
from sourcetrace_v2.app.services.execution import execute_minimal_research_flow
from sourcetrace_v2.app.services.persistence import persist_execution_outcome
from sourcetrace_v2.app.services.readback import load_persisted_execution_view
from sourcetrace_v2.projections.api.readback import project_persisted_execution_view
from sourcetrace_v2.runtime.config.defaults import build_default_runtime_config


def get_persisted_minimal_flow_payload(*, job_id: str, run_id: str, seed_text: str) -> dict[str, object]:
    result_repo = InMemoryResultArtifactRepository()
    receipt_repo = InMemoryReceiptRepository()
    config = build_default_runtime_config()
    llm = StubLlmGateway(config)
    outcome = execute_minimal_research_flow(
        job_id=job_id,
        run_id=run_id,
        seed_text=seed_text,
        llm=llm,
        config=config,
    )
    persist_execution_outcome(outcome=outcome, results=result_repo, receipts=receipt_repo)

    view = load_persisted_execution_view(
        job_id=outcome.job.job_id,
        run_id=outcome.run.run_id,
        results=result_repo,
        receipts=receipt_repo,
    )
    payload = project_persisted_execution_view(view=view)
    payload["job_status"] = outcome.job.status.value
    return payload
