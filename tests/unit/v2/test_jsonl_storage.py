import logging
import json
from pathlib import Path

import pytest

from sourcetrace_v2.adapters.llm.stub import StubLlmGateway
from sourcetrace_v2.adapters.search.stub import StubSearchGateway
from sourcetrace_v2.adapters.storage.jsonl import JsonlReceiptRepository, JsonlResultArtifactRepository
from sourcetrace_v2.app.services.http_api import handle_get_persisted_compiled_artifact_request
from sourcetrace_v2.app.services.compiled_artifacts import build_compiled_artifact
from sourcetrace_v2.app.composition.runtime import RuntimeAssembly
from sourcetrace_v2.app.services.http_api import handle_get_persisted_execution_request
from sourcetrace_v2.app.services.run_use_case import run_and_persist_minimal_flow
from sourcetrace_v2.runtime.config.defaults import build_default_runtime_config
from sourcetrace_v2.core.contracts.trust_metadata import SourceTraceTrustMetadata
from sourcetrace_v2.core.domain.models import ResearchResultArtifact, RetrievedEvidenceCandidate
from sourcetrace_v2.execution.stages.retrieval import _build_retrieval_semantic_fit_diagnostics


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


def test_jsonl_storage_roundtrips_explicit_trust_metadata(tmp_path: Path) -> None:
    results = JsonlResultArtifactRepository(tmp_path)
    metadata = SourceTraceTrustMetadata(
        authority_id="authority-one", jurisdiction_id="US", scope="national",
        provenance="operator", confidence="high",
    )
    artifact = ResearchResultArtifact(
        job_id="job-jsonl-trust-metadata",
        run_id="run-jsonl-trust-metadata",
        result_text="summary",
        evidence_candidates=(
            RetrievedEvidenceCandidate(
                candidate_id="candidate-trust-metadata",
                job_id="job-jsonl-trust-metadata",
                run_id="run-jsonl-trust-metadata",
                provider="fixture",
                query="official guidance",
                title="Official guidance",
                url="https://authority.example.test/guidance",
                snippet="Official guidance snippet.",
                source_type="institutional",
                trust_metadata=metadata,
            ),
        ),
    )
    compiled = build_compiled_artifact(artifact=artifact)

    results.save_result(artifact)
    results.save_compiled_artifact(compiled)

    loaded_artifact = results.get_result(job_id=artifact.job_id, run_id=artifact.run_id)
    loaded_compiled = results.get_compiled_artifact(job_id=artifact.job_id, run_id=artifact.run_id)

    assert loaded_artifact is not None
    assert loaded_compiled is not None
    assert loaded_artifact.evidence_candidates[0].trust_metadata == metadata
    assert loaded_compiled.selected_evidence[0].trust_metadata == metadata


def test_jsonl_storage_roundtrips_semantic_fit_diagnostics(tmp_path: Path) -> None:
    results = JsonlResultArtifactRepository(tmp_path)
    query = "incident response guidance"
    candidates = (
        RetrievedEvidenceCandidate(
            candidate_id="candidate-fit-1",
            job_id="job-jsonl-fit",
            run_id="run-jsonl-fit",
            provider="fixture",
            query=query,
            title="Agency incident response guidance",
            url="https://agency.example.test/guidance/incident-response",
            snippet="Official incident response guidance for operators.",
            rank=1,
            source_type="institutional",
        ),
        RetrievedEvidenceCandidate(
            candidate_id="candidate-fit-2",
            job_id="job-jsonl-fit",
            run_id="run-jsonl-fit",
            provider="fixture",
            query=query,
            title="Agency incident response checklist",
            url="https://agency.example.test/checklists/incident-response",
            snippet="Official checklist for incident response and recovery.",
            rank=2,
            source_type="institutional",
        ),
        RetrievedEvidenceCandidate(
            candidate_id="candidate-fit-3",
            job_id="job-jsonl-fit",
            run_id="run-jsonl-fit",
            provider="fixture",
            query=query,
            title="Agency security overview",
            url="https://agency.example.test/security/overview",
            snippet="Broad security overview.",
            rank=3,
            source_type="institutional",
        ),
    )
    trimmed_candidates = candidates[:2]
    diagnostics = _build_retrieval_semantic_fit_diagnostics(
        query=query,
        pretrim_candidates=candidates,
        trimmed_candidates=trimmed_candidates,
        pretrim_explicit=True,
    )
    artifact = ResearchResultArtifact(
        job_id="job-jsonl-fit",
        run_id="run-jsonl-fit",
        result_text="summary",
        evidence_query=query,
        evidence_candidates=trimmed_candidates,
        pretrim_evidence_candidates=candidates,
        retrieval_diagnostics=diagnostics,
        retrieval_candidate_pool_count=len(candidates),
        retrieval_semantic_fit_status=diagnostics.pretrim.status,
        retrieval_best_focus_coverage=1.0,
    )

    results.save_result(artifact)
    loaded = results.get_result(job_id=artifact.job_id, run_id=artifact.run_id)

    assert loaded is not None
    assert [candidate.title for candidate in loaded.evidence_candidates] == [
        "Agency incident response guidance",
        "Agency incident response checklist",
    ]
    assert [candidate.title for candidate in loaded.pretrim_evidence_candidates] == [
        "Agency incident response guidance",
        "Agency incident response checklist",
        "Agency security overview",
    ]
    assert loaded.retrieval_candidate_pool_count == 3
    assert loaded.retrieval_semantic_fit_status == "sufficient"
    assert loaded.retrieval_best_focus_coverage == 1.0
    assert loaded.retrieval_diagnostics is not None
    assert loaded.retrieval_diagnostics.pretrim.best_candidate_rank == 1


def test_jsonl_storage_reads_old_result_rows_without_semantic_fit_fields(tmp_path: Path) -> None:
    results = JsonlResultArtifactRepository(tmp_path)
    legacy_row = {
        "job_id": "job-jsonl-legacy",
        "run_id": "run-jsonl-legacy",
        "result_text": "summary",
        "summary": "",
        "evidence_query": "incident response guidance",
        "evidence_candidates": [
            {
                "candidate_id": "legacy-1",
                "job_id": "job-jsonl-legacy",
                "run_id": "run-jsonl-legacy",
                "provider": "fixture",
                "query": "incident response guidance",
                "title": "Legacy incident response guidance",
                "url": "https://agency.example.test/guidance/incident-response",
                "snippet": "Official guidance.",
                "rank": 1,
                "source_type": "institutional",
            }
        ],
    }
    results.path.write_text(json.dumps(legacy_row) + "\n", encoding="utf-8")

    loaded = results.get_result(job_id="job-jsonl-legacy", run_id="run-jsonl-legacy")

    assert loaded is not None
    assert [candidate.title for candidate in loaded.evidence_candidates] == ["Legacy incident response guidance"]
    assert [candidate.title for candidate in loaded.pretrim_evidence_candidates] == ["Legacy incident response guidance"]
    assert loaded.retrieval_candidate_pool_count == 1
    assert loaded.retrieval_semantic_fit_status == "unknown"
    assert loaded.retrieval_best_focus_coverage is None
    assert loaded.retrieval_diagnostics is None
