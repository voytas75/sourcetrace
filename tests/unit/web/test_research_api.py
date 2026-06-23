import json
from io import BytesIO
from typing import cast
from wsgiref.util import setup_testing_defaults

from sourcetrace.application import FakeResearchWorker, ResearchJobManager, SearchHit
from sourcetrace.storage import create_in_memory_research_persistence
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
    assert json.loads(status_body)["job"]["job_id"] == job_id
    assert pending_result_status == "202 Accepted"
    assert json.loads(pending_result_body)["status"] == "pending"
    assert run_status == "200 OK"
    assert json.loads(run_body)["job"]["status"] == "done"
    assert result_status == "200 OK"
    assert json.loads(result_body)["result"]["completion_mode"] == "full"
    assert result_html_status == "200 OK"
    assert ("Content-Type", "text/html; charset=utf-8") in result_html_headers
    assert "Structured research report optimized for external reading" in result_html_body
    assert "Evaluation and confidence" in result_html_body
    assert "Sources reviewed" in result_html_body
    assert list_status == "200 OK"
    assert len(json.loads(list_body)["jobs"]) == 1
    assert compiled_status == "200 OK"
    assert json.loads(compiled_body)["artifact"]["artifact_id"] == f"cra-{job_id}"
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
    assert status_status == "200 OK"
    assert json.loads(status_body)["job"]["status"] == "cancelled"


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


def _test_delivery() -> object:
    persistence = create_in_memory_research_persistence()
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
    worker = FakeResearchWorker(persistence, search=TestSearch())
    research = type("ResearchBundle", (), {
        "start_job": manager.start_job,
        "get_job_status": manager.get_job_status,
        "cancel_job": manager.cancel_job,
        "get_job_result": manager.get_job_result,
        "list_jobs": manager.list_jobs,
        "run_job": worker,
    })()
    return create_default_delivery(research=research, research_persistence=persistence)
