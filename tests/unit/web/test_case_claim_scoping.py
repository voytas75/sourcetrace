import json
from datetime import UTC, datetime
from io import BytesIO
from typing import cast
from wsgiref.util import setup_testing_defaults

from sourcetrace.application import CaseCreationRequest, ClaimExtractionRuntime
from sourcetrace.application.extraction import ClaimExtractionOutcome, ClaimExtractionRequest
from sourcetrace.domain import Claim, ClaimEvidenceLink, Document, DocumentChunk
from sourcetrace.domain.types import VerificationVerdict
from sourcetrace.web import SourceTraceWSGIApp, create_default_delivery, create_wsgi_app


def test_wsgi_case_claim_routes_keep_claims_scoped_when_claim_ids_repeat_across_cases() -> None:
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
            exact_text=chunks[0].raw_text,
            source_span_reference=chunks[0].position_reference or "p1",
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
    app = SourceTraceWSGIApp(delivery=delivery)

    for case_id, document_id, text in (
        ("case-news", "doc-news", "Around 18000 customers were affected at the peak of the disruption."),
        ("case-caveat", "doc-caveat", "The minister said the reform package is on track."),
    ):
        _call_wsgi(
            app,
            method="POST",
            path="/api/cases",
            payload={"case_id": case_id, "title": case_id},
        )
        delivery.persistence.documents.save_document(
            Document(
                document_id=document_id,
                case_id=case_id,
                source_type="note",
                source_url=None,
                publisher=None,
                author=None,
                title=document_id,
                published_at=None,
                retrieved_at=datetime(2026, 5, 20, 0, 0, tzinfo=UTC),
                content_hash=f"sha256:{document_id}",
                language="en",
            )
        )
        delivery.persistence.documents.save_chunks(
            (
                DocumentChunk(
                    chunk_id=f"{document_id}:chunk-1",
                    case_id=case_id,
                    document_id=document_id,
                    raw_text=text,
                    start_char=0,
                    end_char=len(text),
                    chunk_index=0,
                    position_reference="p1",
                ),
            )
        )
        _call_wsgi(
            app,
            method="POST",
            path=f"/api/documents/{document_id}/extract-claims",
            payload={},
        )

    news_status, _, news_body = _call_wsgi(
        app,
        method="GET",
        path="/api/cases/case-news/claims",
    )
    caveat_status, _, caveat_body = _call_wsgi(
        app,
        method="GET",
        path="/api/cases/case-caveat/claims",
    )

    assert news_status == "200 OK"
    assert caveat_status == "200 OK"
    assert [claim["exact_text"] for claim in json.loads(news_body)["claims"]] == [
        "Around 18000 customers were affected at the peak of the disruption."
    ]
    assert [claim["exact_text"] for claim in json.loads(caveat_body)["claims"]] == [
        "The minister said the reform package is on track."
    ]


def test_case_html_view_keeps_claim_rows_scoped_when_claim_ids_repeat_across_cases() -> None:
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
            exact_text=chunks[0].raw_text,
            source_span_reference=chunks[0].position_reference or "p1",
            system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
            rationale=None,
        )
        return ClaimExtractionOutcome(
            request=request,
            document=document,
            chunks=chunks,
            claims=(claim,),
            evidence_links=(),
        )

    delivery = create_default_delivery(
        claim_extraction_runtime=ClaimExtractionRuntime(extract_claims=extract_claims)
    )
    app = create_wsgi_app(delivery=delivery)

    for case_id, document_id, text in (
        ("case-news", "doc-news", "Around 18000 customers were affected at the peak of the disruption."),
        ("case-caveat", "doc-caveat", "The minister said the reform package is on track."),
    ):
        delivery.create_case(
            CaseCreationRequest(case_id=case_id, title=case_id, description=None)
        )
        delivery.persistence.documents.save_document(
            Document(
                document_id=document_id,
                case_id=case_id,
                source_type="note",
                source_url=None,
                publisher=None,
                author=None,
                title=document_id,
                published_at=None,
                retrieved_at=datetime(2026, 5, 20, 0, 0, tzinfo=UTC),
                content_hash=f"sha256:{document_id}",
                language="en",
            )
        )
        delivery.persistence.documents.save_chunks(
            (
                DocumentChunk(
                    chunk_id=f"{document_id}:chunk-1",
                    case_id=case_id,
                    document_id=document_id,
                    raw_text=text,
                    start_char=0,
                    end_char=len(text),
                    chunk_index=0,
                    position_reference="p1",
                ),
            )
        )
        delivery.extract_claims(document_id)

    news_status, _, news_body = _call_wsgi(app, method="GET", path="/cases/case-news")
    caveat_status, _, caveat_body = _call_wsgi(app, method="GET", path="/cases/case-caveat")

    assert news_status == "200 OK"
    assert caveat_status == "200 OK"
    assert "Around 18000 customers were affected at the peak of the disruption." in news_body
    assert "The minister said the reform package is on track." not in news_body
    assert "The minister said the reform package is on track." in caveat_body
    assert "Around 18000 customers were affected at the peak of the disruption." not in caveat_body


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
    return (
        str(response["status"]),
        cast(list[tuple[str, str]], response["headers"]),
        response_body,
    )
