import json
from io import BytesIO
from typing import cast
from wsgiref.util import setup_testing_defaults

from sourcetrace.application import (
    FakeResearchWorker,
    ResearchJobManager,
    ResearchJobStartRequest,
    SearchHit,
)
from sourcetrace.application.research_runtime import ResearchSearchError
from sourcetrace.storage import (
    create_file_backed_research_persistence,
    create_in_memory_research_persistence,
    recover_interrupted_research_jobs,
)
from sourcetrace.web import SourceTraceWSGIApp, create_default_delivery


def test_wsgi_research_job_flow() -> None:
    app = SourceTraceWSGIApp(delivery=_test_delivery())

    start_status, _, start_body = _call_wsgi(
        app,
        method="POST",
        path="/api/research/start",
        payload={"owner_id": "user-1", "query": "deep research architecture"},
    )
    start_payload = json.loads(start_body)
    job_id = start_payload["job"]["job_id"]

    status_status, _, status_body = _call_wsgi(
        app,
        method="GET",
        path=f"/api/research/status/{job_id}",
    )
    pending_result_status, _, pending_result_body = _call_wsgi(
        app,
        method="GET",
        path=f"/api/research/result/{job_id}",
    )
    run_status, _, run_body = _call_wsgi(
        app,
        method="POST",
        path=f"/api/research/run/{job_id}",
    )
    result_status, _, result_body = _call_wsgi(
        app,
        method="GET",
        path=f"/api/research/result/{job_id}",
    )
    result_html_status, result_html_headers, result_html_body = _call_wsgi(
        app,
        method="GET",
        path=f"/api/research/result/{job_id}.html",
    )
    list_status, _, list_body = _call_wsgi(
        app,
        method="GET",
        path="/api/research/jobs?owner_id=user-1",
    )
    compiled_status, _, compiled_body = _call_wsgi(
        app,
        method="GET",
        path=f"/api/research/compiled/cra-{job_id}",
    )
    lint_status, _, lint_body = _call_wsgi(
        app,
        method="GET",
        path=f"/api/research/compiled/cra-{job_id}/lint",
    )

    assert start_status == "201 Created"
    assert start_payload["job"]["status"] == "queued"
    assert status_status == "200 OK"
    status_payload = json.loads(status_body)
    assert status_payload["job"]["job_id"] == job_id
    assert status_payload["job"]["planning_analysis"]["analysis_version"] == "planning_analysis_v1_fallback"
    assert status_payload["job"]["planning_analysis"]["execution_mode"]
    assert status_payload["job"]["problem_analysis"]["analysis_version"] == "problem_analyzer_v1"
    assert status_payload["job"]["execution_plan"]["plan_version"] == "planner_v2"
    assert pending_result_status == "202 Accepted"
    assert json.loads(pending_result_body)["status"] == "pending"
    assert run_status == "200 OK"
    assert json.loads(run_body)["job"]["status"] == "done"
    assert result_status == "200 OK"
    result_payload = json.loads(result_body)
    assert result_payload["job"]["termination_reason"] is None
    assert result_payload["result"]["completion_mode"] == "full"
    assert result_payload["result"]["termination_reason"] is None
    assert result_payload["result"]["planning_analysis"]["goal"] == start_payload["job"]["query"]
    assert result_payload["result"]["planning_analysis"]["analysis_version"] == "planning_analysis_v1_fallback"
    assert result_payload["result"]["problem_analysis"]["goal"] == start_payload["job"]["query"]
    assert result_payload["result"]["execution_plan"]["strategy"]
    assert result_payload["result"]["evidence_pack"]["pack_version"] == "evidence_pack_v1"
    assert result_payload["result"]["branch_proposals"]["proposal_version"] == "branch_proposal_v1"
    assert result_payload["result"]["branch_evaluation"]["evaluation_version"] == "branch_evaluator_v1"
    assert result_payload["result"]["reflection"]["reflection_version"] == "reflection_v1"
    assert result_html_status == "200 OK"
    assert ("Content-Type", "text/html; charset=utf-8") in result_html_headers
    assert "Structured research report optimized for external reading" in result_html_body
    assert "Evaluation and confidence" in result_html_body
    assert "Sources reviewed" in result_html_body
    assert list_status == "200 OK"
    assert len(json.loads(list_body)["jobs"]) == 1
    assert compiled_status == "200 OK"
    compiled_payload = json.loads(compiled_body)
    assert compiled_payload["artifact"]["artifact_id"] == f"cra-{job_id}"
    assert compiled_payload["artifact"]["planning_analysis_snapshot"]["analysis_version"] == "planning_analysis_v1_fallback"
    assert compiled_payload["artifact"]["problem_analysis_snapshot"]["analysis_version"] == "problem_analyzer_v1"
    assert compiled_payload["artifact"]["execution_plan_snapshot"]["plan_version"] == "planner_v2"
    assert compiled_payload["artifact"]["reflection_snapshot"]["reflection_version"] == "reflection_v1"
    assert lint_status == "200 OK"
    assert json.loads(lint_body)["lint"]["artifact_id"] == f"cra-{job_id}"


def test_wsgi_research_cancel_flow() -> None:
    app = SourceTraceWSGIApp(delivery=_test_delivery())
    start_status, _, start_body = _call_wsgi(
        app,
        method="POST",
        path="/api/research/start",
        payload={"owner_id": "user-1", "query": "deep research architecture"},
    )
    job_id = json.loads(start_body)["job"]["job_id"]

    cancel_status, _, cancel_body = _call_wsgi(
        app,
        method="POST",
        path=f"/api/research/cancel/{job_id}",
    )
    status_status, _, status_body = _call_wsgi(
        app,
        method="GET",
        path=f"/api/research/status/{job_id}",
    )

    assert start_status == "201 Created"
    assert cancel_status == "200 OK"
    assert json.loads(cancel_body)["job"]["status"] == "cancelled"
    assert json.loads(cancel_body)["job"]["termination_reason"] == "cancelled"
    assert status_status == "200 OK"
    status_payload = json.loads(status_body)
    assert status_payload["job"]["status"] == "cancelled"
    assert status_payload["job"]["termination_reason"] == "cancelled"


def test_wsgi_research_result_reports_terminal_cancelled_instead_of_pending() -> None:
    app = SourceTraceWSGIApp(delivery=_test_delivery())
    _, _, start_body = _call_wsgi(
        app,
        method="POST",
        path="/api/research/start",
        payload={"owner_id": "user-1", "query": "deep research architecture"},
    )
    job_id = json.loads(start_body)["job"]["job_id"]

    cancel_status, _, _ = _call_wsgi(
        app,
        method="POST",
        path=f"/api/research/cancel/{job_id}",
    )
    result_status, _, result_body = _call_wsgi(
        app,
        method="GET",
        path=f"/api/research/result/{job_id}",
    )

    result_payload = json.loads(result_body)
    assert cancel_status == "200 OK"
    assert result_status == "200 OK"
    assert result_payload["status"] == "terminal"
    assert result_payload["termination_reason"] == "cancelled"
    assert result_payload["job"]["termination_reason"] == "cancelled"
    assert result_payload["result"] is None


def test_wsgi_research_status_reports_interrupted_on_recovery(tmp_path) -> None:
    research_root = tmp_path / "research"
    persistence = create_file_backed_research_persistence(research_root)
    manager = ResearchJobManager(persistence)
    start = manager.start_job(
        ResearchJobStartRequest(owner_id="user-1", query="deep research architecture")
    )
    recover_interrupted_research_jobs(research_root)
    recovered_persistence = create_file_backed_research_persistence(research_root)
    app = SourceTraceWSGIApp(delivery=_test_delivery(persistence=recovered_persistence))

    status_status, _, status_body = _call_wsgi(
        app,
        method="GET",
        path=f"/api/research/status/{start.job.job_id}",
    )
    result_status, _, result_body = _call_wsgi(
        app,
        method="GET",
        path=f"/api/research/result/{start.job.job_id}",
    )

    status_payload = json.loads(status_body)
    result_payload = json.loads(result_body)
    assert status_status == "200 OK"
    assert status_payload["job"]["status"] == "error"
    assert status_payload["job"]["termination_reason"] == "interrupted_on_recovery"
    assert result_status == "200 OK"
    assert result_payload["status"] == "terminal"
    assert result_payload["termination_reason"] == "interrupted_on_recovery"
    assert result_payload["job"]["termination_reason"] == "interrupted_on_recovery"


def test_wsgi_research_run_reports_provider_failure_without_salvage() -> None:
    class ImmediateFailureSearch:
        def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
            raise ResearchSearchError("provider failed")

    app = SourceTraceWSGIApp(delivery=_test_delivery(search=ImmediateFailureSearch()))
    _, _, start_body = _call_wsgi(
        app,
        method="POST",
        path="/api/research/start",
        payload={"owner_id": "user-1", "query": "deep research architecture"},
    )
    job_id = json.loads(start_body)["job"]["job_id"]

    run_status, _, run_body = _call_wsgi(
        app,
        method="POST",
        path=f"/api/research/run/{job_id}",
    )
    result_status, _, result_body = _call_wsgi(
        app,
        method="GET",
        path=f"/api/research/result/{job_id}",
    )

    run_payload = json.loads(run_body)
    result_payload = json.loads(result_body)
    assert run_status == "200 OK"
    assert run_payload["job"]["status"] == "error"
    assert run_payload["job"]["termination_reason"] == "provider_failure"
    assert run_payload["result"] is None
    assert result_status == "200 OK"
    assert result_payload["status"] == "terminal"
    assert result_payload["termination_reason"] == "provider_failure"
    assert result_payload["job"]["termination_reason"] == "provider_failure"


def test_wsgi_research_run_reports_partial_salvage_distinct_from_full_success() -> None:
    class SalvagingSearch:
        def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
            if round_number == 1:
                return (
                    SearchHit(
                        url="https://example.test/architecture",
                        title="Architecture",
                        snippet="Deep research architecture summary.",
                    ),
                )
            raise ResearchSearchError("provider failed after first round")

    app = SourceTraceWSGIApp(delivery=_test_delivery(search=SalvagingSearch()))
    _, _, start_body = _call_wsgi(
        app,
        method="POST",
        path="/api/research/start",
        payload={"owner_id": "user-1", "query": "deep research architecture"},
    )
    job_id = json.loads(start_body)["job"]["job_id"]

    run_status, _, run_body = _call_wsgi(
        app,
        method="POST",
        path=f"/api/research/run/{job_id}",
    )
    list_status, _, list_body = _call_wsgi(
        app,
        method="GET",
        path="/api/research/jobs?owner_id=user-1",
    )

    run_payload = json.loads(run_body)
    list_payload = json.loads(list_body)
    assert run_status == "200 OK"
    assert run_payload["job"]["status"] == "done"
    assert run_payload["job"]["termination_reason"] == "partial_salvage"
    assert run_payload["result"]["completion_mode"] == "partial_error"
    assert run_payload["result"]["termination_reason"] == "partial_salvage"
    assert list_status == "200 OK"
    assert list_payload["jobs"][0]["termination_reason"] == "partial_salvage"


def test_wsgi_operational_payloads_do_not_mark_research_ready_when_disabled() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

    ready_status, _, ready_body = _call_wsgi(app, method="GET", path="/api/ready")
    runtime_status, _, runtime_body = _call_wsgi(app, method="GET", path="/api/runtime")
    capabilities_status, _, capabilities_body = _call_wsgi(app, method="GET", path="/api/capabilities")
    console_status, _, console_body = _call_wsgi(app, method="GET", path="/research")

    assert ready_status == "200 OK"
    ready_payload = json.loads(ready_body)
    assert ready_payload["checks"]["research"] is False
    assert ready_payload["checks"]["research_enabled"] is False
    assert ready_payload["diagnostics"]["research"] == {
        "enabled": False,
        "ready": False,
        "status": "disabled",
        "search_backend": "stub",
        "search_configured": False,
    }
    assert runtime_status == "200 OK"
    runtime_payload = json.loads(runtime_body)
    assert runtime_payload["runtime"]["research"] == "disabled"
    assert runtime_payload["runtime"]["research_enabled"] is False
    assert runtime_payload["runtime"]["research_ready"] is False
    assert capabilities_status == "200 OK"
    capabilities_payload = json.loads(capabilities_body)
    assert capabilities_payload["runtime"]["research"] is False
    assert capabilities_payload["runtime"]["research_enabled"] is False
    assert capabilities_payload["runtime"]["research_status"] == "disabled"
    assert "/api/research/start" in capabilities_payload["routes"]["product"]
    assert console_status == "200 OK"
    assert "runtime_notice" in console_body


def test_wsgi_research_start_returns_unavailable_when_runtime_is_not_ready() -> None:
    research = object()
    delivery = create_default_delivery(
        research=research,
        research_persistence=create_in_memory_research_persistence(),
        research_search_backend="searxng",
        research_search_configured=False,
    )
    app = SourceTraceWSGIApp(delivery=delivery)

    start_status, _, start_body = _call_wsgi(
        app,
        method="POST",
        path="/api/research/start",
        payload={"owner_id": "user-1", "query": "deep research architecture"},
    )
    ready_status, _, ready_body = _call_wsgi(app, method="GET", path="/api/ready")
    runtime_status, _, runtime_body = _call_wsgi(app, method="GET", path="/api/runtime")
    capabilities_status, _, capabilities_body = _call_wsgi(app, method="GET", path="/api/capabilities")

    assert start_status == "503 Service Unavailable"
    assert json.loads(start_body) == {"error": "research_unavailable", "status": "unavailable"}
    assert ready_status == "200 OK"
    assert json.loads(ready_body)["diagnostics"]["research"] == {
        "enabled": True,
        "ready": False,
        "status": "not_ready",
        "search_backend": "searxng",
        "search_configured": False,
    }
    assert runtime_status == "200 OK"
    runtime_payload = json.loads(runtime_body)
    assert runtime_payload["runtime"]["research"] == "not_ready"
    assert runtime_payload["runtime"]["research_enabled"] is True
    assert runtime_payload["runtime"]["research_ready"] is False
    assert capabilities_status == "200 OK"
    capabilities_payload = json.loads(capabilities_body)
    assert capabilities_payload["runtime"]["research"] is False
    assert capabilities_payload["runtime"]["research_enabled"] is True
    assert capabilities_payload["runtime"]["research_status"] == "not_ready"


def test_wsgi_research_owner_id_is_normalized_to_lowercase() -> None:
    app = SourceTraceWSGIApp(delivery=_test_delivery())

    start_status, _, start_body = _call_wsgi(
        app,
        method="POST",
        path="/api/research/start",
        payload={"owner_id": "Wojtek", "query": "deep research architecture"},
    )
    start_payload = json.loads(start_body)

    list_status, _, list_body = _call_wsgi(
        app,
        method="GET",
        path="/api/research/jobs?owner_id=wojtek",
    )
    list_payload = json.loads(list_body)

    assert start_status == "201 Created"
    assert start_payload["job"]["owner_id"] == "wojtek"
    assert list_status == "200 OK"
    assert list_payload["owner_id"] == "wojtek"
    assert len(list_payload["jobs"]) == 1
    assert list_payload["jobs"][0]["owner_id"] == "wojtek"


def _call_wsgi(
    app: SourceTraceWSGIApp,
    *,
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
) -> tuple[str, list[tuple[str, str]], str]:
    environ: dict[str, object] = {}
    setup_testing_defaults(cast(dict[str, str], environ))
    body_bytes = json.dumps(payload or {}).encode("utf-8")
    environ["REQUEST_METHOD"] = method
    environ["PATH_INFO"] = path.split("?", 1)[0]
    environ["QUERY_STRING"] = path.split("?", 1)[1] if "?" in path else ""
    environ["CONTENT_LENGTH"] = str(len(body_bytes))
    environ["CONTENT_TYPE"] = "application/json"
    environ["wsgi.input"] = BytesIO(body_bytes)

    captured: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        captured["status"] = status
        captured["headers"] = headers

    body = b"".join(app(environ, start_response)).decode("utf-8")
    return (
        cast(str, captured["status"]),
        cast(list[tuple[str, str]], captured["headers"]),
        body,
    )


def test_wsgi_research_console_and_debug_pages_render() -> None:
    app = SourceTraceWSGIApp(delivery=_test_delivery())

    research_status, _, research_body = _call_wsgi(
        app,
        method="GET",
        path="/research",
    )
    debug_status, _, debug_body = _call_wsgi(
        app,
        method="GET",
        path="/research/debug",
    )

    assert research_status == "200 OK"
    assert "Open debug view" in research_body
    assert "status-chip" in research_body
    assert "Search hits" in research_body
    assert "result_html" not in research_body
    assert debug_status == "200 OK"
    assert "Research debug view" in debug_body
    assert "Back to operator view" in debug_body


def test_research_console_debug_script_surfaces_narrowing_warning_messages() -> None:
    app = SourceTraceWSGIApp(delivery=_test_delivery())

    _, _, start_body = _call_wsgi(
        app,
        method="POST",
        path="/api/research/start",
        payload={"owner_id": "user-1", "query": "deep research architecture"},
    )
    job_id = json.loads(start_body)["job"]["job_id"]
    _call_wsgi(
        app,
        method="POST",
        path=f"/api/research/run/{job_id}",
    )
    debug_status, _, debug_body = _call_wsgi(
        app,
        method="GET",
        path="/research",
    )

    assert debug_status == "200 OK"
    assert "narrowing:" in debug_body
    assert "Search narrowing:" in debug_body


def _test_delivery(
    *,
    persistence=None,
    search=None,
) -> object:
    persistence = persistence or create_in_memory_research_persistence()
    manager = ResearchJobManager(persistence)
    class TestSearch:
        def __call__(self, queries: tuple[str, ...], *, round_number: int) -> tuple[SearchHit, ...]:
            if round_number == 1:
                return (
                    SearchHit(url="https://example.test/architecture", title="Architecture", snippet="Deep research architecture summary."),
                    SearchHit(url="https://example.test/runtime", title="Runtime", snippet="Runtime flow and persistence details."),
                )
            return (
                SearchHit(url="https://example.test/rails", title="Stop rails", snippet="Bounded engine loop and stop rails."),
            )
    worker = FakeResearchWorker(persistence, search=search or TestSearch())
    research = type("ResearchBundle", (), {
        "start_job": manager.start_job,
        "get_job_status": manager.get_job_status,
        "cancel_job": manager.cancel_job,
        "get_job_result": manager.get_job_result,
        "list_jobs": manager.list_jobs,
        "run_job": worker,
    })()
    return create_default_delivery(
        research=research,
        research_persistence=persistence,
        research_search_backend="test_search",
        research_search_configured=True,
    )


def test_default_delivery_uses_supplied_research_persistence_for_reads() -> None:
    from sourcetrace.storage import create_file_backed_research_persistence
    from sourcetrace.web.delivery import create_default_delivery

    persistence = create_file_backed_research_persistence('tmp/test-research-persistence')
    marker = object()
    delivery = create_default_delivery(
        research_persistence=persistence,
        research=marker,
    )

    assert delivery.research_persistence is persistence
