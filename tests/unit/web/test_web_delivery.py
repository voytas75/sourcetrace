import json
from io import BytesIO
from wsgiref.util import setup_testing_defaults

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
    render_report_markdown,
    report_outcome_to_payload,
)
from sourcetrace.web.api import SourceTraceWSGIApp as ModuleSourceTraceWSGIApp
from sourcetrace.web.api import create_wsgi_app as module_create_wsgi_app
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
    assert json.loads(inspect_body)["evidence_links"][0]["chunk_id"] == "chunk-1"
    assert review_status == "200 OK"
    assert report_status == "200 OK"
    assert ("Content-Type", "text/markdown; charset=utf-8") in report_headers
    assert "Accepted for report." in report_body
    assert case_status == "200 OK"
    assert ("Content-Type", "text/html; charset=utf-8") in case_headers
    assert "The bridge reopened after inspection." in case_body


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
