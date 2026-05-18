import json
from io import BytesIO
from typing import cast
from wsgiref.util import setup_testing_defaults

from sourcetrace.domain import Claim, ClaimReviewDecision, DocumentChunk
from sourcetrace.domain.types import (
    AnalystDisposition,
    HumanReviewStatus,
    VerificationVerdict,
)
from sourcetrace.web import SourceTraceWSGIApp, VerificationDeliveryRequest, create_default_delivery


def test_end_to_end_in_memory_verification_review_and_report_flow() -> None:
    delivery = _seeded_delivery()
    claim = Claim(
        claim_id="claim-1",
        case_id="case-1",
        document_id="doc-1",
        chunk_id="chunk-1",
        exact_text="The bridge reopened after inspection.",
        source_span_reference="p1",
        system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
    )

    verify_outcome = delivery.verify_claim(
        VerificationDeliveryRequest(
            claim=claim,
            requested_k=2,
            query_id="query-1",
            retrieval_method="end-to-end-lexical",
        )
    )
    inspection_before_review = delivery.inspect_verification("claim-1")
    review_decision = delivery.record_review(
        ClaimReviewDecision(
            claim_id="claim-1",
            case_id="case-1",
            human_review_status=HumanReviewStatus.REVIEWED_ACCEPT,
            analyst_disposition=AnalystDisposition.CONFIRMED_SUPPORT,
            final_verdict=VerificationVerdict.SUPPORT,
            review_notes="Accepted after analyst review.",
        )
    )
    inspection_after_review = delivery.inspect_verification("claim-1")
    report_outcome = delivery.assemble_case_report("case-1")
    app = SourceTraceWSGIApp(delivery=delivery)
    inspect_status, _, inspect_body = _call_wsgi(
        app,
        method="GET",
        path="/api/claims/claim-1/verification",
    )
    report_status, _, report_body = _call_wsgi(
        app,
        method="GET",
        path="/api/reports/case-1.json",
    )

    assert verify_outcome.verification_outcome.verification.verdict is VerificationVerdict.SUPPORT
    assert inspection_before_review is not None
    assert inspection_before_review.has_review is False
    assert review_decision.human_review_status is HumanReviewStatus.REVIEWED_ACCEPT
    assert inspection_after_review is not None
    assert inspection_after_review.has_review is True
    assert inspection_after_review.has_report_entry is True
    assert report_outcome.case_report.generated_claim_ids == ("claim-1",)
    assert inspect_status == "200 OK"
    assert json.loads(inspect_body)["evidence_summary"]["has_report_entry"] is True
    assert report_status == "200 OK"
    assert json.loads(report_body)["case_report"]["entries"][0]["summary_text"] == (
        "Accepted after analyst review."
    )


def _seeded_delivery():
    delivery = create_default_delivery()
    delivery.persistence.documents.save_chunks(
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
            DocumentChunk(
                chunk_id="chunk-2",
                case_id="case-1",
                document_id="doc-1",
                raw_text="Bridge engineers said the reopening followed safety checks.",
                start_char=64,
                end_char=123,
                chunk_index=2,
            ),
        )
    )
    return delivery


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

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        response["status"] = status
        response["headers"] = headers

    response_body = b"".join(app(environ, start_response)).decode("utf-8")
    return str(response["status"]), cast(list[tuple[str, str]], response["headers"]), response_body
