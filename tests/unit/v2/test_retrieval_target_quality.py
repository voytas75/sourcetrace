import json

from sourcetrace_v2.app.composition.runtime import build_preferred_search_backed_stubbed_jsonl_runtime
from sourcetrace_v2.app.services.http_api import handle_run_minimal_flow_request


def test_run_flow_promotes_more_targeted_official_candidate_before_selection(tmp_path) -> None:
    runtime = build_preferred_search_backed_stubbed_jsonl_runtime(
        base_dir=tmp_path,
        base_url="http://127.0.0.1:8080",
        unified_search_web=lambda query, count=10: [
            {
                "url": "https://gov.example.test/labour/remote-work",
                "title": "Official labour ministry portal",
                "snippet": "Broad official portal page covering remote work obligations.",
            },
            {
                "url": "https://legal.example.test/remote-work-reporting-obligations",
                "title": "Detailed legal commentary on reporting obligations",
                "snippet": "Focused commentary on the exact reporting obligation question.",
            },
            {
                "url": "https://gov.example.test/labour/remote-work-reporting-faq",
                "title": "Official FAQ on remote work reporting obligations for employers in Poland",
                "snippet": "Specific official FAQ on remote work reporting obligations for employers in Poland.",
            },
        ],
    )

    response = handle_run_minimal_flow_request(
        job_id="job-target-quality",
        run_id="run-target-quality",
        seed_text="remote work reporting obligations Poland employer official guidance",
        runtime=runtime,
    )

    payload = json.loads(response.body)

    assert response.status_code == 201
    assert payload["artifact"]["present"] is True
    assert payload["evidence_input"]["candidates"][0]["title"] == (
        "Official FAQ on remote work reporting obligations for employers in Poland"
    )
    assert payload["evidence_input"]["candidates"][1]["title"] == "Official labour ministry portal"
    assert payload["selected_evidence"]["items"][0]["title"] == (
        "Official FAQ on remote work reporting obligations for employers in Poland"
    )
    assert "top_source=procedural_admin_unified_search:Official FAQ on remote work reporting obligations for employers in Poland" in payload["artifact"]["summary"]
