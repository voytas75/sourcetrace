import json

from sourcetrace_v2.adapters.storage.memory import InMemoryReceiptRepository, InMemoryResultArtifactRepository
from sourcetrace_v2.app.composition.minimal_flow import run_minimal_flow
from sourcetrace_v2.app.composition.runtime import RuntimeAssembly
from sourcetrace_v2.app.services.http_api import handle_get_persisted_execution_request, handle_run_minimal_flow_request
from sourcetrace_v2.execution.receipts.persisted_collector import PersistedReceiptCollector
from sourcetrace_v2.runtime.config.defaults import build_default_runtime_config
from sourcetrace_v2.adapters.llm.stub import StubLlmGateway
from sourcetrace_v2.runtime.logging.setup import configure_logging


def test_handle_run_minimal_flow_request_returns_created_json_response() -> None:
    config = build_default_runtime_config()
    runtime = RuntimeAssembly(
        config=config,
        llm=StubLlmGateway(config),
        results=InMemoryResultArtifactRepository(),
        receipts=InMemoryReceiptRepository(),
        logger=configure_logging(config.logging),
    )

    response = handle_run_minimal_flow_request(
        job_id="job-http-run",
        run_id="run-http-run",
        seed_text="test query",
        runtime=runtime,
    )

    payload = json.loads(response.body)
    assert response.status_code == 201
    assert response.content_type.startswith("application/json")
    assert payload["job_id"] == "job-http-run"
    assert payload["run_id"] == "run-http-run"
    assert payload["status"] == "found"
    assert payload["artifact"]["present"] is True
    assert payload["rollup"]["total_tokens"] == 384


def test_handle_get_persisted_execution_request_returns_projection() -> None:
    result_repo = InMemoryResultArtifactRepository()
    receipt_repo = InMemoryReceiptRepository()
    job, run, artifact, collector = run_minimal_flow(
        job_id="job-http-get",
        run_id="run-http-get",
        seed_text="please use fallback",
    )
    persisted = PersistedReceiptCollector(repository=receipt_repo)
    for receipt in collector.stage_receipts:
        persisted.append_stage(receipt)
    for receipt in collector.llm_receipts:
        persisted.append_llm(receipt)
    result_repo.save_result(artifact)

    response = handle_get_persisted_execution_request(
        job_id=job.job_id,
        run_id=run.run_id,
        results=result_repo,
        receipts=receipt_repo,
    )

    payload = json.loads(response.body)
    assert response.status_code == 200
    assert payload["status"] == "found"
    assert payload["job_id"] == "job-http-get"
    assert payload["run_id"] == "run-http-get"
    assert payload["artifact"]["present"] is True
    assert payload["rollup"]["degraded_calls"] == 4


def test_handle_get_persisted_execution_request_returns_not_found() -> None:
    result_repo = InMemoryResultArtifactRepository()
    receipt_repo = InMemoryReceiptRepository()

    response = handle_get_persisted_execution_request(
        job_id="missing-job",
        run_id="missing-run",
        results=result_repo,
        receipts=receipt_repo,
    )

    payload = json.loads(response.body)
    assert response.status_code == 404
    assert payload["status"] == "not_found"
    assert payload["artifact"]["present"] is False


def test_handle_get_persisted_execution_request_returns_incomplete() -> None:
    result_repo = InMemoryResultArtifactRepository()
    receipt_repo = InMemoryReceiptRepository()
    job, run, _artifact, collector = run_minimal_flow(
        job_id="job-http-incomplete",
        run_id="run-http-incomplete",
        seed_text="test query",
    )
    persisted = PersistedReceiptCollector(repository=receipt_repo)
    for receipt in collector.stage_receipts:
        persisted.append_stage(receipt)
    for receipt in collector.llm_receipts:
        persisted.append_llm(receipt)

    response = handle_get_persisted_execution_request(
        job_id=job.job_id,
        run_id=run.run_id,
        results=result_repo,
        receipts=receipt_repo,
    )

    payload = json.loads(response.body)
    assert response.status_code == 202
    assert payload["status"] == "incomplete"
    assert payload["artifact"]["present"] is False
    assert payload["receipts"]["llm_count"] == 4
