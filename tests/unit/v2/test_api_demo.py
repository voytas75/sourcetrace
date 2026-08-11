from sourcetrace_v2.app.services.api_demo import get_persisted_minimal_flow_payload


def test_api_demo_builds_complete_stubbed_runtime() -> None:
    payload = get_persisted_minimal_flow_payload(
        job_id="job-api-demo",
        run_id="run-api-demo",
        seed_text="Climate policy evidence.",
    )

    assert payload["job_status"] == "done"
