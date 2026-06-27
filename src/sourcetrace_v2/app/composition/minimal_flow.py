from __future__ import annotations

from sourcetrace_v2.adapters.llm.stub import StubLlmGateway
from sourcetrace_v2.app.services.execution import execute_minimal_research_flow
from sourcetrace_v2.runtime.config.defaults import build_default_runtime_config
from sourcetrace_v2.runtime.logging.setup import configure_logging


def run_minimal_flow(*, job_id: str, run_id: str, seed_text: str):
    config = build_default_runtime_config()
    llm = StubLlmGateway(config)
    logger = configure_logging(config.logging)
    outcome = execute_minimal_research_flow(
        job_id=job_id,
        run_id=run_id,
        seed_text=seed_text,
        llm=llm,
        config=config,
        logger=logger,
    )
    return outcome.job, outcome.run, outcome.artifact, outcome.collector
