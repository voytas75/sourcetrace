import json
from io import BytesIO
from typing import cast
from wsgiref.util import setup_testing_defaults

from sourcetrace.web import SourceTraceWSGIApp, create_default_delivery


def test_wsgi_research_job_flow() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

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
    list_status, _, list_body = _call_wsgi(
        app,
        method="GET",
        path="/api/research/jobs?owner_id=user-1",
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
    assert list_status == "200 OK"
    assert len(json.loads(list_body)["jobs"]) == 1


def test_wsgi_research_cancel_flow() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())
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
