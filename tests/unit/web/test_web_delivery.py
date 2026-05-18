import json
from dataclasses import FrozenInstanceError
from io import BytesIO
from wsgiref.util import setup_testing_defaults

import pytest

from sourcetrace.domain import Claim, ClaimReviewDecision, DocumentChunk
from sourcetrace.domain.types import (
    AnalystDisposition,
    HumanReviewStatus,
    VerificationVerdict,
)
from sourcetrace.storage import create_in_memory_persistence
from sourcetrace.web import (
    PersistenceReportAssembler,
    SourceTraceDelivery,
    SourceTraceWSGIApp,
    VerificationDeliveryRequest,
    create_default_delivery,
    create_wsgi_app,
    create_wsgi_server,
    run_local_server,
    render_report_markdown,
    report_outcome_to_payload,
)
from sourcetrace.web.api import SourceTraceWSGIApp as ModuleSourceTraceWSGIApp
from sourcetrace.web.api import create_wsgi_app as module_create_wsgi_app
from sourcetrace.web.api import create_wsgi_server as module_create_wsgi_server
from sourcetrace.web.api import run_local_server as module_run_local_server
from sourcetrace.web.delivery import (
    PersistenceReportAssembler as ModulePersistenceReportAssembler,
)
from sourcetrace.web.delivery import SourceTraceDelivery as ModuleSourceTraceDelivery
from sourcetrace.web.delivery import (
    VerificationDeliveryRequest as ModuleVerificationDeliveryRequest,
)
from sourcetrace.web.delivery import create_default_delivery as module_create_default_delivery


def test_web_package_re_exports_delivery_surface() -> None:
    assert SourceTraceDelivery is ModuleSourceTraceDelivery
    assert SourceTraceWSGIApp is ModuleSourceTraceWSGIApp
    assert PersistenceReportAssembler is ModulePersistenceReportAssembler
    assert VerificationDeliveryRequest is ModuleVerificationDeliveryRequest
    assert create_default_delivery is module_create_default_delivery
    assert create_wsgi_app is module_create_wsgi_app
    assert create_wsgi_server is module_create_wsgi_server
    assert run_local_server is module_run_local_server


def test_create_wsgi_server_returns_frozen_server_bundle_with_bound_app() -> None:
    delivery = _seeded_delivery()

    server_runtime = create_wsgi_server(
        host="127.0.0.1",
        port=0,
        delivery=delivery,
    )

    assert server_runtime.host == "127.0.0.1"
    assert server_runtime.port == 0
    assert server_runtime.app.delivery is delivery
    assert callable(server_runtime.server.serve_forever)
    assert server_runtime.server.server_port >= 0

    with pytest.raises(FrozenInstanceError):
        setattr(server_runtime, "port", 8080)

    server_runtime.server.server_close()


def test_create_wsgi_server_uses_bound_port_when_ephemeral_port_requested() -> None:
    server_runtime = create_wsgi_server(host="127.0.0.1", port=0)

    try:
        assert server_runtime.server.server_port > 0
    finally:
        server_runtime.server.server_close()


def test_run_local_server_reports_bound_address_and_closes_server() -> None:
    messages: list[str] = []

    runtime = run_local_server(host="127.0.0.1", port=0, announce=messages.append)

    try:
        assert runtime.host == "127.0.0.1"
        assert runtime.server.server_port > 0
        assert messages == [
            f"SourceTrace local server listening on http://127.0.0.1:{runtime.server.server_port}"
        ]
    finally:
        runtime.server.server_close()


def test_web_module_main_delegates_to_local_server_runtime() -> None:
    from sourcetrace.web import __main__ as web_main

    events: list[str] = []

    class _FakeServer:
        def serve_forever(self) -> None:
            events.append("serve_forever")

        def server_close(self) -> None:
            events.append("server_close")

    class _FakeRuntime:
        def __init__(self) -> None:
            self.server = _FakeServer()

    original = web_main.run_local_server
    web_main.run_local_server = lambda: _FakeRuntime()
    try:
        assert web_main.main() == 0
        assert events == ["serve_forever", "server_close"]
    finally:
        web_main.run_local_server = original


def test_package_metadata_exposes_uv_ready_console_entrypoint() -> None:
    from sourcetrace.web.__main__ import main

    assert callable(main)


def test_delivery_service_runs_and_inspects_verification_path() -> None:
    delivery = _seeded_delivery()
    claim = _claim()

    outcome = delivery.verify_claim(
        VerificationDeliveryRequest(
            claim=claim,
            requested_k=2,
            query_id="query-1",
            retrieval_method="api-lexical",
        )
    )
    inspection = delivery.inspect_verification("claim-1")

    assert outcome.verification_outcome.verification.verdict is VerificationVerdict.SUPPORT
    assert inspection is not None
    assert inspection.claim is claim
    assert inspection.verification.verdict is VerificationVerdict.SUPPORT
    assert tuple(link.chunk_id for link in inspection.evidence_links) == ("chunk-1",)
    assert inspection.evidence_count == 1
    assert inspection.supporting_evidence_count == 1
    assert inspection.contradicting_evidence_count == 0
    assert inspection.insufficient_evidence_count == 0
    assert inspection.has_review is False
    assert inspection.has_report_entry is False


def test_delivery_service_assembles_json_and_markdown_report_output() -> None:
    delivery = _seeded_delivery()
    delivery.verify_claim(VerificationDeliveryRequest(claim=_claim(), requested_k=2))
    delivery.record_review(
        ClaimReviewDecision(
            claim_id="claim-1",
            case_id="case-1",
            human_review_status=HumanReviewStatus.REVIEWED_ACCEPT,
            analyst_disposition=AnalystDisposition.CONFIRMED_SUPPORT,
            final_verdict=VerificationVerdict.SUPPORT,
            review_notes="Analyst confirmed the bridge reopened.",
        )
    )

    outcome = delivery.assemble_case_report("case-1")
    payload = report_outcome_to_payload(outcome)
    markdown = render_report_markdown(outcome)

    assert payload["case_report"]["case_id"] == "case-1"
    assert payload["case_report"]["generated_claim_ids"] == ["claim-1"]
    assert payload["case_report"]["entries"][0]["supporting_chunk_ids"] == ["chunk-1"]
    assert "Analyst confirmed the bridge reopened." in markdown
    assert "- Final verdict: support" in markdown


def test_wsgi_app_exposes_verification_inspection_and_report_routes() -> None:
    delivery = _seeded_delivery()
    app = create_wsgi_app(delivery=delivery)
    claim_payload = {
        "claim_id": "claim-1",
        "case_id": "case-1",
        "document_id": "doc-1",
        "chunk_id": "chunk-1",
        "exact_text": "The bridge reopened after inspection.",
        "source_span_reference": "p1",
        "system_verdict": "insufficient_evidence",
        "rationale": None,
    }

    verify_status, _, verify_body = _call_wsgi(
        app,
        method="POST",
        path="/api/verify",
        payload={"claim": claim_payload, "requested_k": 2},
    )
    inspect_status, _, inspect_body = _call_wsgi(
        app,
        method="GET",
        path="/api/claims/claim-1/verification",
    )
    review_status, _, _ = _call_wsgi(
        app,
        method="POST",
        path="/api/reviews",
        payload={
            "claim_id": "claim-1",
            "case_id": "case-1",
            "human_review_status": "reviewed_accept",
            "analyst_disposition": "confirmed_support",
            "final_verdict": "support",
            "review_notes": "Accepted for report.",
        },
    )
    report_status, report_headers, report_body = _call_wsgi(
        app,
        method="GET",
        path="/api/reports/case-1.md",
    )
    case_status, case_headers, case_body = _call_wsgi(
        app,
        method="GET",
        path="/cases/case-1",
    )

    assert verify_status == "200 OK"
    assert json.loads(verify_body)["verification"]["verdict"] == "support"
    assert inspect_status == "200 OK"
    inspection_payload = json.loads(inspect_body)
    assert inspection_payload["evidence_links"][0]["chunk_id"] == "chunk-1"
    assert inspection_payload["evidence_summary"] == {
        "evidence_count": 1,
        "supporting_evidence_count": 1,
        "contradicting_evidence_count": 0,
        "insufficient_evidence_count": 0,
        "has_review": False,
        "has_report_entry": False,
    }
    assert review_status == "200 OK"
    assert report_status == "200 OK"
    assert ("Content-Type", "text/markdown; charset=utf-8") in report_headers
    assert "Accepted for report." in report_body
    assert case_status == "200 OK"
    assert ("Content-Type", "text/html; charset=utf-8") in case_headers
    assert "The bridge reopened after inspection." in case_body


def test_wsgi_app_returns_status_payloads_for_missing_or_invalid_resources() -> None:
    app = create_wsgi_app(delivery=_seeded_delivery())

    missing_inspection_status, _, missing_inspection_body = _call_wsgi(
        app,
        method="GET",
        path="/api/claims/missing-claim/verification",
    )
    missing_report_status, _, missing_report_body = _call_wsgi(
        app,
        method="GET",
        path="/api/reports/missing-case.json",
    )
    invalid_review_status, _, invalid_review_body = _call_wsgi(
        app,
        method="POST",
        path="/api/reviews",
        payload={
            "claim_id": "claim-1",
            "case_id": "case-1",
        },
    )

    assert missing_inspection_status == "404 Not Found"
    assert json.loads(missing_inspection_body) == {
        "error": "verification_not_found",
        "status": "missing",
    }
    assert missing_report_status == "404 Not Found"
    assert json.loads(missing_report_body) == {
        "error": "report_not_found",
        "status": "missing",
    }
    assert invalid_review_status == "400 Bad Request"
    assert json.loads(invalid_review_body) == {
        "error": "human_review_status is required.",
        "status": "invalid_request",
    }


def _seeded_delivery() -> SourceTraceDelivery:
    persistence = create_in_memory_persistence()
    persistence.documents.save_chunks(
        (
            DocumentChunk(
                chunk_id="chunk-1",
                case_id="case-1",
                document_id="doc-1",
                raw_text="City officials confirmed the bridge reopened after inspection.",
                start_char=0,
                end_char=63,
                chunk_index=1,
            ),
        )
    )
    return create_default_delivery(persistence=persistence)


def _claim() -> Claim:
    return Claim(
        claim_id="claim-1",
        case_id="case-1",
        document_id="doc-1",
        chunk_id="chunk-1",
        exact_text="The bridge reopened after inspection.",
        source_span_reference="p1",
        system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
    )


def _call_wsgi(
    app: SourceTraceWSGIApp,
    *,
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
) -> tuple[str, list[tuple[str, str]], str]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else b""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
    }
    setup_testing_defaults(environ)
    response: dict[str, object] = {}

    def start_response(
        status: str,
        headers: list[tuple[str, str]],
    ) -> None:
        response["status"] = status
        response["headers"] = headers

    response_body = b"".join(app(environ, start_response)).decode("utf-8")
    return (
        str(response["status"]),
        list(response["headers"]),
        response_body,
    )
