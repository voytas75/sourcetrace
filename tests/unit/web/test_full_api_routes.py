import json
from datetime import UTC, datetime
from io import BytesIO
from typing import cast
from wsgiref.util import setup_testing_defaults

from sourcetrace.application import ClaimExtractionRuntime
from sourcetrace.application.extraction import ClaimExtractionOutcome, ClaimExtractionRequest
from sourcetrace.domain import Claim, ClaimEvidenceLink, Document, DocumentChunk
from sourcetrace.domain.types import VerificationVerdict
from sourcetrace.web import SourceTraceWSGIApp, create_default_delivery


def test_wsgi_product_resource_flow_and_read_surfaces() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

    case_status, _, case_body = _call_wsgi(
        app,
        method="POST",
        path="/api/cases",
        payload={
            "case_id": "case-1",
            "title": "Bridge reopening",
            "description": "Track public claims.",
        },
    )
    document_status, _, document_body = _call_wsgi(
        app,
        method="POST",
        path="/api/cases/case-1/documents",
        payload={
            "document_id": "doc-1",
            "source_type": "url",
            "source_url": "https://example.test/bridge",
            "publisher": "Example News",
            "author": "Analyst",
            "title": "Bridge update",
            "published_at": "2026-05-18T00:00:00+00:00",
            "retrieved_at": "2026-05-18T00:05:00+00:00",
            "content_hash": "sha256:abc123",
            "language": "en",
        },
    )
    prepare_status, _, prepare_body = _call_wsgi(
        app,
        method="POST",
        path="/api/documents/doc-1/prepare",
        payload={
            "raw_text": "The bridge reopened after inspection.\n\nTraffic resumed.",
            "chunking_method": "paragraph-v1",
        },
    )
    verify_status, _, _ = _call_wsgi(
        app,
        method="POST",
        path="/api/verify",
        payload={
            "claim": {
                "claim_id": "claim-1",
                "case_id": "case-1",
                "document_id": "doc-1",
                "chunk_id": "doc-1:chunk-1",
                "exact_text": "The bridge reopened after inspection.",
                "source_span_reference": "p1",
                "system_verdict": "insufficient_evidence",
                "rationale": None,
            },
            "requested_k": 2,
        },
    )

    cases_status, _, cases_body = _call_wsgi(app, method="GET", path="/api/cases")
    get_case_status, _, get_case_body = _call_wsgi(
        app,
        method="GET",
        path="/api/cases/case-1",
    )
    docs_status, _, docs_body = _call_wsgi(
        app,
        method="GET",
        path="/api/cases/case-1/documents",
    )
    get_doc_status, _, get_doc_body = _call_wsgi(
        app,
        method="GET",
        path="/api/documents/doc-1",
    )
    chunks_status, _, chunks_body = _call_wsgi(
        app,
        method="GET",
        path="/api/documents/doc-1/chunks",
    )
    claims_status, _, claims_body = _call_wsgi(
        app,
        method="GET",
        path="/api/cases/case-1/claims",
    )
    claim_status, _, claim_body = _call_wsgi(
        app,
        method="GET",
        path="/api/claims/claim-1",
    )
    evidence_status, _, evidence_body = _call_wsgi(
        app,
        method="GET",
        path="/api/claims/claim-1/evidence",
    )
    verification_status, _, verification_body = _call_wsgi(
        app,
        method="GET",
        path="/api/claims/claim-1/verification",
    )
    report_status, _, report_body = _call_wsgi(
        app,
        method="GET",
        path="/api/reports/case-1",
    )

    assert case_status == "201 Created"
    assert json.loads(case_body)["case"]["case_id"] == "case-1"
    assert document_status == "201 Created"
    assert json.loads(document_body)["document"]["case_id"] == "case-1"
    assert prepare_status == "200 OK"
    assert json.loads(prepare_body)["chunks"][0]["chunk_id"] == "doc-1:chunk-1"
    assert verify_status == "200 OK"
    assert cases_status == "200 OK"
    assert json.loads(cases_body)["cases"][0]["case_id"] == "case-1"
    assert get_case_status == "200 OK"
    assert json.loads(get_case_body)["case"]["document_ids"] == ["doc-1"]
    assert docs_status == "200 OK"
    assert json.loads(docs_body)["documents"][0]["document_id"] == "doc-1"
    assert get_doc_status == "200 OK"
    assert json.loads(get_doc_body)["document"]["document_id"] == "doc-1"
    assert chunks_status == "200 OK"
    assert len(json.loads(chunks_body)["chunks"]) == 2
    assert claims_status == "200 OK"
    assert json.loads(claims_body)["claims"][0]["claim_id"] == "claim-1"
    assert claim_status == "200 OK"
    assert json.loads(claim_body)["claim"]["claim_id"] == "claim-1"
    assert evidence_status == "200 OK"
    assert json.loads(evidence_body)["evidence_links"][0]["chunk_id"] == "doc-1:chunk-1"
    assert verification_status == "200 OK"
    assert json.loads(verification_body)["verification"]["verdict"] == "support"
    assert report_status == "200 OK"
    assert json.loads(report_body)["case_report"]["case_id"] == "case-1"


def test_wsgi_extract_claims_route_uses_configured_runtime() -> None:
    document = _document()
    chunks = (
        DocumentChunk(
            chunk_id="chunk-1",
            case_id="case-1",
            document_id="doc-1",
            raw_text="The bridge reopened after inspection.",
            start_char=0,
            end_char=39,
            chunk_index=0,
            position_reference="p1",
        ),
    )

    def extract_claims(
        request: ClaimExtractionRequest,
        *,
        document: Document,
        chunks: tuple[DocumentChunk, ...],
    ) -> ClaimExtractionOutcome:
        claim = Claim(
            claim_id="claim-1",
            case_id=request.case_id,
            document_id=request.document_id,
            chunk_id=chunks[0].chunk_id,
            exact_text="The bridge reopened after inspection.",
            source_span_reference="p1",
            system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
            rationale=None,
        )
        evidence = ClaimEvidenceLink(
            claim_id="claim-1",
            document_id=document.document_id,
            chunk_id=chunks[0].chunk_id,
            evidence_rank=1,
            evidence_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
            rationale="Initial extraction link.",
            snippet=chunks[0].raw_text,
            score=None,
        )
        return ClaimExtractionOutcome(
            request=request,
            document=document,
            chunks=chunks,
            claims=(claim,),
            evidence_links=(evidence,),
        )

    delivery = create_default_delivery(
        claim_extraction_runtime=ClaimExtractionRuntime(extract_claims=extract_claims)
    )
    delivery.persistence.documents.save_document(document)
    delivery.persistence.documents.save_chunks(chunks)
    app = SourceTraceWSGIApp(delivery=delivery)

    status, _, body = _call_wsgi(
        app,
        method="POST",
        path="/api/documents/doc-1/extract-claims",
        payload={"extraction_method": "test-runtime"},
    )
    claim_status, _, claim_body = _call_wsgi(
        app,
        method="GET",
        path="/api/claims/claim-1",
    )

    assert status == "200 OK"
    payload = json.loads(body)
    assert payload["claims"][0]["claim_id"] == "claim-1"
    assert payload["evidence_links"][0]["rationale"] == "Initial extraction link."
    assert claim_status == "200 OK"
    assert json.loads(claim_body)["claim"]["exact_text"] == (
        "The bridge reopened after inspection."
    )


def test_wsgi_persists_and_reads_credibility_assessment() -> None:
    def draft_credibility(prompt: str):
        return type(
            "_Result",
            (),
            {"text": "Credibility draft reached persistence.", "model": "test-model"},
        )()

    delivery = create_default_delivery(
        credibility_draft=draft_credibility,
        credibility_assessed_at=lambda: datetime(2026, 5, 19, 11, 0, tzinfo=UTC),
    )
    delivery.persistence.documents.save_document(_document())
    app = SourceTraceWSGIApp(delivery=delivery)

    post_status, _, _ = _call_wsgi(
        app,
        method="POST",
        path="/api/documents/doc-1/credibility",
        payload={"assessment_method": "llm_draft_v1"},
    )
    get_status, _, get_body = _call_wsgi(
        app,
        method="GET",
        path="/api/documents/doc-1/credibility",
    )

    assert post_status == "200 OK"
    assert get_status == "200 OK"
    assert json.loads(get_body)["credibility_assessment"]["notes"] == (
        "Credibility draft reached persistence."
    )


def test_wsgi_operational_endpoints_describe_runtime_and_capabilities() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

    health_status, _, health_body = _call_wsgi(app, method="GET", path="/api/health")
    ready_status, _, ready_body = _call_wsgi(app, method="GET", path="/api/ready")
    runtime_status, _, runtime_body = _call_wsgi(app, method="GET", path="/api/runtime")
    capabilities_status, _, capabilities_body = _call_wsgi(
        app,
        method="GET",
        path="/api/capabilities",
    )

    assert health_status == "200 OK"
    assert json.loads(health_body) == {"status": "ok"}
    assert ready_status == "200 OK"
    assert json.loads(ready_body)["checks"]["delivery"] is True
    assert runtime_status == "200 OK"
    assert json.loads(runtime_body)["runtime"]["entrypoint"] == "wsgi"
    assert capabilities_status == "200 OK"
    assert "/api/cases/{case_id}/documents" in json.loads(capabilities_body)["routes"]["product"]
    assert "/api/dev/documents" in json.loads(capabilities_body)["routes"]["dev"]


def _document() -> Document:
    return Document(
        document_id="doc-1",
        case_id="case-1",
        source_type="url",
        source_url="https://example.test/bridge",
        publisher="Example News",
        author="Analyst",
        title="Bridge update",
        published_at=datetime(2026, 5, 18, 0, 0, tzinfo=UTC),
        retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
        content_hash="sha256:abc123",
        language="en",
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

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        response["status"] = status
        response["headers"] = headers

    response_body = b"".join(app(environ, start_response)).decode("utf-8")
    return str(response["status"]), cast(list[tuple[str, str]], response["headers"]), response_body
