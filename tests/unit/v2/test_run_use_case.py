from sourcetrace_v2.adapters.llm.stub import StubLlmGateway
from sourcetrace_v2.adapters.storage.memory import InMemoryReceiptRepository, InMemoryResultArtifactRepository
from sourcetrace_v2.app.services.run_use_case import run_and_persist_minimal_flow
from sourcetrace_v2.runtime.config.defaults import build_default_runtime_config


def test_run_and_persist_minimal_flow_returns_found_view() -> None:
    config = build_default_runtime_config()
    llm = StubLlmGateway(config)
    result_repo = InMemoryResultArtifactRepository()
    receipt_repo = InMemoryReceiptRepository()

    view = run_and_persist_minimal_flow(
        job_id="job-run-use-case",
        run_id="run-run-use-case",
        seed_text="test query",
        llm=llm,
        results=result_repo,
        receipts=receipt_repo,
        config=config,
    )

    assert view.status.value == "found"
    assert view.artifact is not None
    assert view.rollup.total_tokens == 384
    assert len(view.llm_receipts) == 4
