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
    case_creation_request_from_payload,
    case_to_payload,
    chunk_to_payload,
    claim_extraction_outcome_to_payload,
    claim_from_payload,
    create_default_delivery,
    document_credibility_assessment_to_payload,
    document_from_payload,
    document_preparation_outcome_to_payload,
    document_to_payload,
    render_case_review_html,
    render_report_markdown,
    report_outcome_to_payload,
    review_decision_from_payload,
    review_decision_to_payload,
    evidence_link_to_payload,
    claim_to_payload,
    verification_inspection_to_payload,
    verification_outcome_to_payload,
)
from sourcetrace.application import DocumentPreparationRequest, SourceIngestionRequest


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
        parts = _path_parts(path)
        if method == "GET" and path == "/":
            return self._render_home(start_response)
        if method == "GET" and path == "/api/health":
            return _json_response(start_response, "200 OK", {"status": "ok"})
        if method == "GET" and path == "/api/ready":
            return _json_response(
                start_response,
                "200 OK",
                self.delivery.readiness_payload(),
            )
        if method == "GET" and path == "/api/runtime":
            return _json_response(
                start_response,
                "200 OK",
                self.delivery.runtime_payload(),
            )
        if method == "GET" and path == "/api/capabilities":
            return _json_response(
                start_response,
                "200 OK",
                self.delivery.capabilities_payload(),
            )
        if parts == ("api", "cases"):
            if method == "GET":
                return self._list_cases(start_response)
            if method == "POST":
                return self._create_case(environ, start_response)
        if len(parts) == 3 and parts[:2] == ("api", "cases"):
            if method == "GET":
                return self._get_case(parts[2], start_response)
        if len(parts) == 4 and parts[:2] == ("api", "cases"):
            case_id = parts[2]
            if parts[3] == "documents":
                if method == "GET":
                    return self._list_case_documents(case_id, start_response)
                if method == "POST":
                    return self._create_case_document(
                        case_id,
                        environ,
                        start_response,
                    )
            if parts[3] == "claims" and method == "GET":
                return self._list_case_claims(case_id, start_response)
        if len(parts) == 3 and parts[:2] == ("api", "documents"):
            if method == "GET":
                return self._get_document(parts[2], start_response)
        if len(parts) == 4 and parts[:2] == ("api", "documents"):
            document_id = parts[2]
            if parts[3] == "chunks" and method == "GET":
                return self._list_document_chunks(document_id, start_response)
            if parts[3] == "prepare" and method == "POST":
                return self._prepare_document(document_id, environ, start_response)
            if parts[3] == "extract-claims" and method == "POST":
                return self._extract_document_claims(
                    document_id,
                    environ,
                    start_response,
                )
            if parts[3] == "credibility":
                if method == "POST":
                    return self._assess_document_credibility(
                        path,
                        environ,
                        start_response,
                    )
                if method == "GET":
                    return self._get_document_credibility(
                        document_id,
                        start_response,
                    )
        if len(parts) == 3 and parts[:2] == ("api", "claims"):
            if method == "GET":
                return self._get_claim(parts[2], start_response)
        if len(parts) == 4 and parts[:2] == ("api", "claims"):
            claim_id = parts[2]
            if parts[3] == "verification" and method == "GET":
                return self._inspect_claim(path, start_response)
            if parts[3] == "evidence" and method == "GET":
                return self._list_claim_evidence(claim_id, start_response)
            if parts[3] == "review" and method == "GET":
                return self._get_claim_review(claim_id, start_response)
        if method == "POST" and path == "/api/verify":
            return self._verify_claim(environ, start_response)
        if method == "POST" and path == "/api/dev/documents":
            return self._seed_document(environ, start_response)
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

    def _render_home(
        self,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        return _html_response(
            start_response,
            "200 OK",
            _render_home_html(),
        )

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

    def _create_case(
        self,
        environ: WsgiEnviron,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        payload = _read_json(environ)
        outcome = self.delivery.create_case(case_creation_request_from_payload(payload))
        return _json_response(
            start_response,
            "201 Created",
            {"case": case_to_payload(outcome.case)},
        )

    def _list_cases(
        self,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        return _json_response(
            start_response,
            "200 OK",
            {"cases": [case_to_payload(case) for case in self.delivery.list_cases()]},
        )

    def _get_case(
        self,
        case_id: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        case = self.delivery.get_case(case_id)
        if case is None:
            return _missing_response(start_response, "case", case_id)
        return _json_response(
            start_response,
            "200 OK",
            {"case": case_to_payload(case)},
        )

    def _create_case_document(
        self,
        case_id: str,
        environ: WsgiEnviron,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        payload = dict(_read_json(environ))
        payload["case_id"] = case_id
        document = document_from_payload(payload)
        outcome = self.delivery.ingest_document(
            SourceIngestionRequest(
                case_id=case_id,
                document_id=document.document_id,
                source_type=document.source_type,
                source_locator=document.source_url,
            ),
            document,
        )
        if outcome is None:
            return _missing_response(start_response, "case", case_id)
        return _json_response(
            start_response,
            "201 Created",
            {"document": document_to_payload(outcome.document)},
        )

    def _list_case_documents(
        self,
        case_id: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        documents = self.delivery.list_documents_for_case(case_id)
        if documents is None:
            return _missing_response(start_response, "case", case_id)
        return _json_response(
            start_response,
            "200 OK",
            {"documents": [document_to_payload(document) for document in documents]},
        )

    def _get_document(
        self,
        document_id: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        document = self.delivery.get_document(document_id)
        if document is None:
            return _missing_response(start_response, "document", document_id)
        return _json_response(
            start_response,
            "200 OK",
            {"document": document_to_payload(document)},
        )

    def _prepare_document(
        self,
        document_id: str,
        environ: WsgiEnviron,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        document = self.delivery.get_document(document_id)
        if document is None:
            return _missing_response(start_response, "document", document_id)
        payload = _read_json(environ)
        raw_text = str(payload.get("raw_text") or "")
        outcome = self.delivery.prepare_document(
            DocumentPreparationRequest(
                case_id=document.case_id,
                document_id=document.document_id,
                chunking_method=_optional_str(payload.get("chunking_method")),
            ),
            raw_text,
        )
        if outcome is None:
            return _missing_response(start_response, "document", document_id)
        return _json_response(
            start_response,
            "200 OK",
            document_preparation_outcome_to_payload(outcome),
        )

    def _list_document_chunks(
        self,
        document_id: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        chunks = self.delivery.list_chunks_for_document(document_id)
        if chunks is None:
            return _missing_response(start_response, "document", document_id)
        return _json_response(
            start_response,
            "200 OK",
            {"chunks": [chunk_to_payload(chunk) for chunk in chunks]},
        )

    def _extract_document_claims(
        self,
        document_id: str,
        environ: WsgiEnviron,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        payload = _read_json(environ)
        if self.delivery.get_document(document_id) is None:
            return _missing_response(start_response, "document", document_id)
        outcome = self.delivery.extract_claims(
            document_id,
            extraction_method=_optional_str(payload.get("extraction_method")),
        )
        if outcome is None:
            return _json_response(
                start_response,
                "501 Not Implemented",
                {"error": "claim_extraction_not_configured", "status": "disabled"},
            )
        return _json_response(
            start_response,
            "200 OK",
            claim_extraction_outcome_to_payload(outcome),
        )

    def _list_case_claims(
        self,
        case_id: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        claims = self.delivery.list_claims_for_case(case_id)
        if claims is None:
            return _missing_response(start_response, "case", case_id)
        return _json_response(
            start_response,
            "200 OK",
            {"claims": [claim_to_payload(claim) for claim in claims]},
        )

    def _get_claim(
        self,
        claim_id: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        claim = self.delivery.get_claim(claim_id)
        if claim is None:
            return _missing_response(start_response, "claim", claim_id)
        return _json_response(
            start_response,
            "200 OK",
            {"claim": claim_to_payload(claim)},
        )

    def _list_claim_evidence(
        self,
        claim_id: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        evidence_links = self.delivery.list_claim_evidence(claim_id)
        if evidence_links is None:
            return _missing_response(start_response, "claim", claim_id)
        return _json_response(
            start_response,
            "200 OK",
            {
                "evidence_links": [
                    evidence_link_to_payload(link) for link in evidence_links
                ]
            },
        )

    def _get_claim_review(
        self,
        claim_id: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        review = self.delivery.get_claim_review(claim_id)
        if review is None:
            return _missing_response(start_response, "review", claim_id)
        return _json_response(
            start_response,
            "200 OK",
            {"review_decision": review_decision_to_payload(review)},
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
            {"review_decision": review_decision_to_payload(review_decision)},
        )

    def _seed_document(
        self,
        environ: WsgiEnviron,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        payload = _read_json(environ)
        document = self.delivery.persistence.documents.save_document(
            document_from_payload(payload)
        )
        return _json_response(
            start_response,
            "201 Created",
            {"document": document_to_payload(document)},
        )

    def _assess_document_credibility(
        self,
        path: str,
        environ: WsgiEnviron,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        document_id = path.removeprefix("/api/documents/").removesuffix(
            "/credibility"
        )
        if not path.endswith("/credibility") or not document_id:
            return _json_response(
                start_response,
                "404 Not Found",
                {"error": "not_found"},
            )
        payload = _read_json(environ)
        outcome = self.delivery.assess_document_credibility(
            document_id,
            assessment_method=_optional_str(payload.get("assessment_method")),
        )
        if outcome is None:
            return _json_response(
                start_response,
                "404 Not Found",
                {"error": "credibility_assessment_not_found", "status": "missing"},
            )
        return _json_response(
            start_response,
            "200 OK",
            {
                "credibility_assessment": document_credibility_assessment_to_payload(
                    outcome.assessment
                )
            },
        )

    def _get_document_credibility(
        self,
        document_id: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        assessment = self.delivery.get_document_credibility(document_id)
        if assessment is None:
            return _json_response(
                start_response,
                "404 Not Found",
                {"error": "credibility_assessment_not_found", "status": "missing"},
            )
        return _json_response(
            start_response,
            "200 OK",
            {
                "credibility_assessment": document_credibility_assessment_to_payload(
                    assessment
                )
            },
        )

    def _render_report(
        self,
        path: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        report_ref = path.removeprefix("/api/reports/").strip("/")
        if report_ref and (not report_ref.endswith(".md")):
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


def _path_parts(path: str) -> tuple[str, ...]:
    return tuple(part for part in path.strip("/").split("/") if part)


def _missing_response(
    start_response: StartResponse,
    resource_type: str,
    resource_id: str,
) -> Iterable[bytes]:
    return _json_response(
        start_response,
        "404 Not Found",
        {
            "error": f"{resource_type}_not_found",
            "status": "missing",
            "resource_type": resource_type,
            "resource_id": resource_id,
        },
    )


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


def _render_home_html() -> str:
    return (
        "<!doctype html>"
        "<html><head><title>SourceTrace Local</title></head>"
        "<body>"
        "<h1>SourceTrace local server</h1>"
        "<p>Available routes:</p>"
        "<ul>"
        "<li><code>GET /api/health</code></li>"
        "<li><code>GET /api/ready</code></li>"
        "<li><code>GET /api/runtime</code></li>"
        "<li><code>GET /api/capabilities</code></li>"
        "<li><code>POST /api/cases</code></li>"
        "<li><code>GET /api/cases</code></li>"
        "<li><code>GET /api/cases/{case_id}</code></li>"
        "<li><code>POST /api/cases/{case_id}/documents</code></li>"
        "<li><code>GET /api/cases/{case_id}/documents</code></li>"
        "<li><code>GET /api/cases/{case_id}/claims</code></li>"
        "<li><code>GET /api/documents/{document_id}</code></li>"
        "<li><code>POST /api/documents/{document_id}/prepare</code></li>"
        "<li><code>GET /api/documents/{document_id}/chunks</code></li>"
        "<li><code>POST /api/documents/{document_id}/extract-claims</code></li>"
        "<li><code>POST /api/verify</code></li>"
        "<li><code>POST /api/dev/documents</code></li>"
        "<li><code>GET /api/claims/{claim_id}</code></li>"
        "<li><code>GET /api/claims/{claim_id}/verification</code></li>"
        "<li><code>GET /api/claims/{claim_id}/evidence</code></li>"
        "<li><code>GET /api/claims/{claim_id}/review</code></li>"
        "<li><code>POST /api/reviews</code></li>"
        "<li><code>GET /api/reports/{case_id}</code></li>"
        "<li><code>GET /api/reports/{case_id}.json</code></li>"
        "<li><code>GET /api/reports/{case_id}.md</code></li>"
        "<li><code>POST /api/documents/{document_id}/credibility</code></li>"
        "<li><code>GET /api/documents/{document_id}/credibility</code></li>"
        "<li><code>GET /cases/{case_id}</code></li>"
        "</ul>"
        "<p>Use the API endpoints or the case route for smoke testing.</p>"
        "</body></html>"
    )


__all__ = [
    "SourceTraceServerRuntime",
    "SourceTraceWSGIApp",
    "create_wsgi_app",
    "create_wsgi_server",
    "run_local_server",
]
