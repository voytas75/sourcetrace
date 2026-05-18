"""Pure-stdlib WSGI API for the minimal delivery surface."""

import json
from collections.abc import Callable, Iterable
from contextlib import suppress
from dataclasses import dataclass
from typing import Any
from wsgiref.simple_server import WSGIServer, make_server

from sourcetrace.web.delivery import (
    SourceTraceDelivery,
    VerificationDeliveryRequest,
    claim_from_payload,
    create_default_delivery,
    render_case_review_html,
    render_report_markdown,
    report_outcome_to_payload,
    review_decision_from_payload,
    verification_inspection_to_payload,
    verification_outcome_to_payload,
)


StartResponse = Callable[[str, list[tuple[str, str]]], None]
WsgiEnviron = dict[str, Any]


@dataclass(frozen=True)
class SourceTraceServerRuntime:
    """Small local server bundle for running the WSGI app."""

    host: str
    port: int
    app: "SourceTraceWSGIApp"
    server: WSGIServer


@dataclass(frozen=True)
class SourceTraceWSGIApp:
    """Small WSGI adapter exposing verification and report routes."""

    delivery: SourceTraceDelivery

    def __call__(
        self,
        environ: WsgiEnviron,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = str(environ.get("PATH_INFO", "/"))

        try:
            return self._dispatch(method, path, environ, start_response)
        except ValueError as exc:
            return _json_response(
                start_response,
                "400 Bad Request",
                {"error": str(exc), "status": "invalid_request"},
            )

    def _dispatch(
        self,
        method: str,
        path: str,
        environ: WsgiEnviron,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        if method == "POST" and path == "/api/verify":
            return self._verify_claim(environ, start_response)
        if method == "GET" and path.startswith("/api/claims/"):
            return self._inspect_claim(path, start_response)
        if method == "POST" and path == "/api/reviews":
            return self._record_review(environ, start_response)
        if method == "GET" and path.startswith("/api/reports/"):
            return self._render_report(path, start_response)
        if method == "GET" and path.startswith("/cases/"):
            case_id = path.removeprefix("/cases/").strip("/")
            return _html_response(
                start_response,
                "200 OK",
                render_case_review_html(self.delivery, case_id),
            )
        return _json_response(start_response, "404 Not Found", {"error": "not_found"})

    def _verify_claim(
        self,
        environ: WsgiEnviron,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        payload = _read_json(environ)
        claim = claim_from_payload(_object_payload(payload, "claim"))
        outcome = self.delivery.verify_claim(
            VerificationDeliveryRequest(
                claim=claim,
                requested_k=int(payload.get("requested_k", 3)),
                query_id=_optional_str(payload.get("query_id")),
                retrieval_method=_optional_str(payload.get("retrieval_method")),
                document_ids=tuple(
                    str(document_id)
                    for document_id in payload.get("document_ids", ())
                ),
            )
        )
        return _json_response(
            start_response,
            "200 OK",
            verification_outcome_to_payload(outcome),
        )

    def _inspect_claim(
        self,
        path: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        claim_id = path.removeprefix("/api/claims/").removesuffix("/verification")
        if not path.endswith("/verification") or not claim_id:
            return _json_response(
                start_response,
                "404 Not Found",
                {"error": "not_found"},
            )
        inspection = self.delivery.inspect_verification(claim_id)
        if inspection is None:
            return _json_response(
                start_response,
                "404 Not Found",
                {"error": "verification_not_found", "status": "missing"},
            )
        return _json_response(
            start_response,
            "200 OK",
            verification_inspection_to_payload(inspection),
        )

    def _record_review(
        self,
        environ: WsgiEnviron,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        payload = _read_json(environ)
        review_decision = self.delivery.record_review(
            review_decision_from_payload(payload)
        )
        return _json_response(
            start_response,
            "200 OK",
            {
                "review_decision": {
                    "claim_id": review_decision.claim_id,
                    "case_id": review_decision.case_id,
                    "human_review_status": review_decision.human_review_status.value,
                    "analyst_disposition": (
                        review_decision.analyst_disposition.value
                        if review_decision.analyst_disposition is not None
                        else None
                    ),
                    "final_verdict": (
                        review_decision.final_verdict.value
                        if review_decision.final_verdict is not None
                        else None
                    ),
                    "review_notes": review_decision.review_notes,
                }
            },
        )

    def _render_report(
        self,
        path: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        report_ref = path.removeprefix("/api/reports/").strip("/")
        if report_ref.endswith(".json"):
            case_id = report_ref.removesuffix(".json")
            outcome = self.delivery.assemble_case_report(case_id)
            if not outcome.entries:
                return _json_response(
                    start_response,
                    "404 Not Found",
                    {"error": "report_not_found", "status": "missing"},
                )
            return _json_response(
                start_response,
                "200 OK",
                report_outcome_to_payload(outcome),
            )
        if report_ref.endswith(".md"):
            case_id = report_ref.removesuffix(".md")
            outcome = self.delivery.assemble_case_report(case_id)
            if not outcome.entries:
                return _json_response(
                    start_response,
                    "404 Not Found",
                    {"error": "report_not_found", "status": "missing"},
                )
            return _text_response(
                start_response,
                "200 OK",
                "text/markdown; charset=utf-8",
                render_report_markdown(outcome),
            )
        return _json_response(start_response, "404 Not Found", {"error": "not_found"})


def create_wsgi_app(
    delivery: SourceTraceDelivery | None = None,
) -> SourceTraceWSGIApp:
    """Create the default WSGI app for local analyst/API use."""

    return SourceTraceWSGIApp(delivery=delivery or create_default_delivery())


def create_wsgi_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    delivery: SourceTraceDelivery | None = None,
) -> SourceTraceServerRuntime:
    """Create a local stdlib WSGI server around the default app."""

    app = create_wsgi_app(delivery=delivery)
    server = make_server(host, port, app)
    return SourceTraceServerRuntime(
        host=host,
        port=port,
        app=app,
        server=server,
    )


def run_local_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    delivery: SourceTraceDelivery | None = None,
    announce: Callable[[str], None] = print,
) -> SourceTraceServerRuntime:
    """Create and announce the local SourceTrace server runtime."""

    runtime = create_wsgi_server(host=host, port=port, delivery=delivery)
    bound_port = runtime.server.server_port
    runtime = SourceTraceServerRuntime(
        host=runtime.host,
        port=bound_port,
        app=runtime.app,
        server=runtime.server,
    )
    try:
        announce(
            f"SourceTrace local server listening on http://{runtime.host}:{runtime.port}"
        )
        return runtime
    except Exception:
        with suppress(Exception):
            runtime.server.server_close()
        raise


def _read_json(environ: WsgiEnviron) -> dict[str, object]:
    try:
        content_length = int(environ.get("CONTENT_LENGTH") or "0")
    except ValueError:
        content_length = 0
    body = environ.get("wsgi.input").read(content_length) if content_length else b"{}"
    if not body:
        return {}
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON request body must be an object.")
    return payload


def _object_payload(
    payload: dict[str, object],
    key: str,
) -> dict[str, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object.")
    return value


def _json_response(
    start_response: StartResponse,
    status: str,
    payload: dict[str, object],
) -> Iterable[bytes]:
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    start_response(
        status,
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


def _html_response(
    start_response: StartResponse,
    status: str,
    body_text: str,
) -> Iterable[bytes]:
    return _text_response(
        start_response,
        status,
        "text/html; charset=utf-8",
        body_text,
    )


def _text_response(
    start_response: StartResponse,
    status: str,
    content_type: str,
    body_text: str,
) -> Iterable[bytes]:
    body = body_text.encode("utf-8")
    start_response(
        status,
        [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


__all__ = [
    "SourceTraceServerRuntime",
    "SourceTraceWSGIApp",
    "create_wsgi_app",
    "create_wsgi_server",
    "run_local_server",
]
