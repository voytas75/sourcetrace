import io
import logging

from sourcetrace_v2.adapters.llm.stub import StubLlmGateway
from sourcetrace_v2.adapters.search.stub import StubSearchGateway
from sourcetrace_v2.app.services.execution import execute_minimal_research_flow
from sourcetrace_v2.runtime.config.defaults import build_default_runtime_config
from sourcetrace_v2.runtime.logging.json_formatter import JsonFormatter
from sourcetrace_v2.runtime.logging.text_formatter import TextFormatter


def test_execution_flow_emits_json_logs_with_correlation_fields() -> None:
    config = build_default_runtime_config()
    llm = StubLlmGateway(config)
    search = StubSearchGateway()
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("sourcetrace_v2.test.json")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False

    outcome = execute_minimal_research_flow(
        job_id="job-log-json",
        run_id="run-log-json",
        seed_text="test query",
        llm=llm,
        search=search,
        config=config,
        logger=logger,
    )

    output = stream.getvalue()
    assert outcome.job.status.value == "done"
    assert '"job_id": "job-log-json"' in output
    assert '"run_id": "run-log-json"' in output
    assert '"event_name": "job.started"' in output
    assert '"event_name": "job.completed"' in output
    assert '"event_name": "stage.started"' in output
    assert '"event_name": "stage.finished"' in output
    assert '"stage_id": "planning"' in output


def test_execution_flow_emits_text_logs_with_stage_context() -> None:
    config = build_default_runtime_config()
    llm = StubLlmGateway(config)
    search = StubSearchGateway()
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(TextFormatter())
    logger = logging.getLogger("sourcetrace_v2.test.text")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False

    execute_minimal_research_flow(
        job_id="job-log-text",
        run_id="run-log-text",
        seed_text="test query",
        llm=llm,
        search=search,
        config=config,
        logger=logger,
    )

    output = stream.getvalue()
    assert "research flow started" in output
    assert "stage started" in output
    assert "stage finished" in output
    assert "job-log-text" in output
    assert "run-log-text" in output
