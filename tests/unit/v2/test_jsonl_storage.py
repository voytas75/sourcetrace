import logging
from pathlib import Path

import pytest

from sourcetrace_v2.adapters.llm.stub import StubLlmGateway
from sourcetrace_v2.adapters.search.stub import StubSearchGateway
from sourcetrace_v2.adapters.storage.jsonl import JsonlReceiptRepository, JsonlResultArtifactRepository
from sourcetrace_v2.app.services.http_api import handle_get_persisted_compiled_artifact_request
from sourcetrace_v2.app.composition.runtime import RuntimeAssembly
from sourcetrace_v2.app.services.http_api import handle_get_persisted_execution_request
from sourcetrace_v2.app.services.run_use_case import run_and_persist_minimal_flow
from sourcetrace_v2.runtime.config.defaults import build_default_runtime_config


def test_jsonl_storage_roundtrip_supports_run_use_case(tmp_path: Path) -> None:
    config = build_default_runtime_config()
    llm = StubLlmGateway(config)
    results = JsonlResultArtifactRepository(tmp_path)
    receipts = JsonlReceiptRepository(tmp_path)

    view = run_and_persist_minimal_flow(
        job_id="job-jsonl",
        run_id="run-jsonl",
        seed_text="test query",
        llm=llm,
        search=StubSearchGateway(),
        results=results,
        receipts=receipts,
        config=config,
    )

    assert view.status.value == "found"
    assert view.artifact is not None
    assert len(view.artifact.evidence_candidates) == 3
    assert view.rollup.total_tokens == 384
    assert len(view.stage_receipts) == 10
    assert len(view.llm_receipts) == 4


def test_jsonl_storage_can_back_http_get_readback(tmp_path: Path) -> None:
    config = build_default_runtime_config()
    llm = StubLlmGateway(config)
    results = JsonlResultArtifactRepository(tmp_path)
    receipts = JsonlReceiptRepository(tmp_path)
    run_and_persist_minimal_flow(
        job_id="job-jsonl-http",
        run_id="run-jsonl-http",
        seed_text="please use fallback",
        llm=llm,
        search=StubSearchGateway(),
        results=results,
        receipts=receipts,
        config=config,
    )

    runtime = RuntimeAssembly(
        config=config,
        llm=llm,
        search=StubSearchGateway(),
        results=results,
        receipts=receipts,
        logger=logging.getLogger("test-jsonl"),
    )

    response = handle_get_persisted_execution_request(
        job_id="job-jsonl-http",
        run_id="run-jsonl-http",
        runtime=runtime,
    )

    assert response.status_code == 200
    assert '"status": "found"' in response.body
    assert '"degraded_calls": 4' in response.body
    assert '"candidate_count": 3' in response.body


def test_jsonl_storage_preserves_execution_source_type_readback_shape(tmp_path: Path) -> None:
    config = build_default_runtime_config()
    llm = StubLlmGateway(config)
    results = JsonlResultArtifactRepository(tmp_path)
    receipts = JsonlReceiptRepository(tmp_path)
    run_and_persist_minimal_flow(
        job_id="job-jsonl-source-type",
        run_id="run-jsonl-source-type",
        seed_text="official guidance",
        llm=llm,
        search=StubSearchGateway(),
        results=results,
        receipts=receipts,
        config=config,
    )

    runtime = RuntimeAssembly(
        config=config,
        llm=llm,
        search=StubSearchGateway(),
        results=results,
        receipts=receipts,
        logger=logging.getLogger("test-jsonl-source-type"),
    )

    response = handle_get_persisted_execution_request(
        job_id="job-jsonl-source-type",
        run_id="run-jsonl-source-type",
        runtime=runtime,
    )

    assert response.status_code == 200
    assert '"source_type": ' in response.body


def test_jsonl_storage_preserves_compiled_judgment_readback_shape(tmp_path: Path) -> None:
    config = build_default_runtime_config()
    llm = StubLlmGateway(config)
    results = JsonlResultArtifactRepository(tmp_path)
    receipts = JsonlReceiptRepository(tmp_path)
    run_and_persist_minimal_flow(
        job_id="job-jsonl-compiled",
        run_id="run-jsonl-compiled",
        seed_text="official tax filing deadline guidance",
        llm=llm,
        search=StubSearchGateway(),
        results=results,
        receipts=receipts,
        config=config,
    )

    runtime = RuntimeAssembly(
        config=config,
        llm=llm,
        search=StubSearchGateway(),
        results=results,
        receipts=receipts,
        logger=logging.getLogger("test-jsonl-compiled"),
    )

    response = handle_get_persisted_compiled_artifact_request(
        job_id="job-jsonl-compiled",
        run_id="run-jsonl-compiled",
        runtime=runtime,
    )

    assert response.status_code == 200
    assert '"selected_evidence_contract_version": "authority-relevance-judgment-contract-v1"' in response.body
    assert '"contract_version": "authority-relevance-judgment-contract-v1"' in response.body
    assert '"answer_fit"' in response.body


def test_jsonl_storage_tolerates_truncated_trailing_result_line(tmp_path: Path) -> None:
    results = JsonlResultArtifactRepository(tmp_path)
    results.save_result(
        artifact=__import__('sourcetrace_v2.core.domain.models', fromlist=['ResearchResultArtifact']).ResearchResultArtifact(
            job_id='job-tail',
            run_id='run-tail',
            result_text='ok',
        )
    )
    results.path.write_text(results.path.read_text(encoding='utf-8') + '{"job_id":"broken"', encoding='utf-8')

    loaded = results.get_result(job_id='job-tail', run_id='run-tail')

    assert loaded is not None
    assert loaded.result_text == 'ok'


def test_jsonl_storage_raises_on_nontrailing_corruption(tmp_path: Path) -> None:
    results = JsonlResultArtifactRepository(tmp_path)
    results.path.write_text(
        '{"job_id":"broken"\n'
        '{"job_id":"job-ok","run_id":"run-ok","result_text":"ok","summary":"","evidence_query":"","evidence_candidates":[]}',
        encoding='utf-8',
    )

    with pytest.raises(ValueError):
        results.get_result(job_id='job-ok', run_id='run-ok')
