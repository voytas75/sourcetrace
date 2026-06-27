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
from sourcetrace_v2.app.composition.runtime import RuntimeAssembly
from sourcetrace_v2.app.services.http_api import handle_run_minimal_flow_request
from sourcetrace_v2.runtime.config.defaults import build_default_runtime_config
from sourcetrace_v2.adapters.llm.stub import StubLlmGateway
from sourcetrace_v2.runtime.logging.setup import configure_logging


def get_persisted_minimal_flow_payload(*, job_id: str, run_id: str, seed_text: str) -> dict[str, object]:
    config = build_default_runtime_config()
    runtime = RuntimeAssembly(
        config=config,
        llm=StubLlmGateway(config),
        results=InMemoryResultArtifactRepository(),
        receipts=InMemoryReceiptRepository(),
        logger=configure_logging(config.logging),
    )
    response = handle_run_minimal_flow_request(
        job_id=job_id,
        run_id=run_id,
        seed_text=seed_text,
        runtime=runtime,
    )
    import json

    payload = json.loads(response.body)
    payload["job_status"] = "done"
    return payload
