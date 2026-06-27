from __future__ import annotations

from sourcetrace_v2.app.composition.runtime import RuntimeAssembly
from sourcetrace_v2.core.contracts.read_models import PersistedViewStatus
from sourcetrace_v2.projections.api.http import HttpResponse, json_response
from sourcetrace_v2.projections.api.readback import project_persisted_execution_view
from sourcetrace_v2.app.services.readback import load_persisted_execution_view
from sourcetrace_v2.app.services.run_use_case import run_and_persist_minimal_flow


def handle_run_minimal_flow_request(*, job_id: str, run_id: str, seed_text: str, runtime: RuntimeAssembly) -> HttpResponse:
    view = run_and_persist_minimal_flow(
        job_id=job_id,
        run_id=run_id,
        seed_text=seed_text,
        llm=runtime.llm,
        search=runtime.search,
        results=runtime.results,
        receipts=runtime.receipts,
        config=runtime.config,
        logger=runtime.logger,
    )
    payload = project_persisted_execution_view(view=view)
    return json_response(payload, status_code=201)


def handle_get_persisted_execution_request(*, job_id: str, run_id: str, runtime: RuntimeAssembly) -> HttpResponse:
    view = load_persisted_execution_view(job_id=job_id, run_id=run_id, results=runtime.results, receipts=runtime.receipts)
    payload = project_persisted_execution_view(view=view)
    if view.status is PersistedViewStatus.NOT_FOUND:
        return json_response(payload, status_code=404)
    if view.status is PersistedViewStatus.INCOMPLETE:
        return json_response(payload, status_code=202)
    return json_response(payload)
