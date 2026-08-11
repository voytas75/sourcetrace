from sourcetrace_v2.app.services.persistence_demo import run_persisted_minimal_flow


def test_persisted_demo_uses_stub_search_and_returns_a_complete_view() -> None:
    result = run_persisted_minimal_flow(
        job_id="demo-job",
        run_id="demo-run",
        seed_text="provider-free demo",
    )

    assert result["status"] == "found"
    assert result["job_id"] == "demo-job"
    assert result["run_id"] == "demo-run"
    assert result["job_status"] == "done"
    assert result["artifact_text"]
