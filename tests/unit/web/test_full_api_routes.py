import json
from datetime import UTC, datetime
from io import BytesIO
from typing import cast
from wsgiref.util import setup_testing_defaults

from sourcetrace.application import (
    CaseCreationRequest,
    ClaimExtractionRuntime,
    ContinuityPackRequest,
)
from sourcetrace.application.extraction import ClaimExtractionOutcome, ClaimExtractionRequest
from sourcetrace.domain import Case, Claim, ClaimEvidenceLink, Document, DocumentChunk
from sourcetrace.domain.types import VerificationVerdict
from sourcetrace.llm.models import LlmGenerationResult
from sourcetrace.web import (
    SourceTraceWSGIApp,
    create_default_delivery,
    render_case_review_html,
)
from sourcetrace.storage import FileBackedCaseRepository, create_in_memory_persistence


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
    case_payload = json.loads(case_body)
    assert case_payload["case"]["case_id"] == "case-1"
    assert case_payload["case"]["continuity_pack"] == {
        "assigned": False,
        "title": None,
        "source_artifact_path": None,
    }
    assert case_payload["status"] == "ready"
    assert case_payload["resource"] == "case"
    assert case_payload["resource_id"] == "case-1"
    assert case_payload["next_step"] == "POST /api/cases/case-1/documents"
    assert document_status == "201 Created"
    document_payload = json.loads(document_body)
    assert document_payload["document"]["case_id"] == "case-1"
    assert document_payload["status"] == "ready"
    assert document_payload["resource"] == "document"
    assert document_payload["resource_id"] == "doc-1"
    assert document_payload["next_step"] == "POST /api/documents/doc-1/prepare"
    assert prepare_status == "200 OK"
    prepare_payload = json.loads(prepare_body)
    assert prepare_payload["status"] == "ready"
    assert prepare_payload["resource"] == "document_preparation"
    assert prepare_payload["resource_id"] == "doc-1"
    assert prepare_payload["next_step"] == "POST /api/documents/doc-1/extract-claims"
    prepare_payload = json.loads(prepare_body)
    assert prepare_payload["chunks"][0]["chunk_id"] == "doc-1:chunk-1"
    assert prepare_payload["diagnostics"]["chunk_count"] == 2
    assert prepare_payload["diagnostics"]["status"] == "ready"
    assert verify_status == "200 OK"
    assert cases_status == "200 OK"
    assert json.loads(cases_body)["cases"][0]["case_id"] == "case-1"
    assert json.loads(cases_body)["cases"][0]["continuity_pack"] == {
        "assigned": False,
        "title": None,
        "source_artifact_path": None,
    }
    assert get_case_status == "200 OK"
    assert json.loads(get_case_body)["case"]["document_ids"] == ["doc-1"]
    assert json.loads(get_case_body)["case"]["continuity_pack"] == {
        "assigned": False,
        "title": None,
        "source_artifact_path": None,
    }
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
    assert payload["status"] == "ready"
    assert payload["resource"] == "claim_extraction"
    assert payload["resource_id"] == "doc-1"
    assert payload["next_step"] == "GET /api/cases/case-1/claims"
    assert payload["claims"][0]["claim_id"] == "claim-1"
    assert payload["claims"][0]["exact_text"] == (
        "The bridge reopened after inspection."
    )
    assert payload["evidence_links"][0]["rationale"] == "Initial extraction link."
    assert payload["diagnostics"]["claim_count"] == 1
    assert payload["diagnostics"]["status"] == "ready"
    assert claim_status == "200 OK"
    assert json.loads(claim_body)["claim"]["exact_text"] == (
        "The bridge reopened after inspection."
    )



def test_wsgi_extract_claims_route_reports_empty_diagnostics_when_runtime_returns_no_claims() -> None:
    document = _document()
    chunks = (
        DocumentChunk(
            chunk_id="chunk-1",
            case_id="case-1",
            document_id="doc-1",
            raw_text="Very short ambiguous note.",
            start_char=0,
            end_char=26,
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
        return ClaimExtractionOutcome(
            request=request,
            document=document,
            chunks=chunks,
            claims=(),
            evidence_links=(),
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

    assert status == "200 OK"
    payload = json.loads(body)
    assert payload["status"] == "empty"
    assert payload["resource"] == "claim_extraction"
    assert payload["resource_id"] == "doc-1"
    assert payload["next_step"] == (
        "Inspect /api/documents/doc-1/chunks and retry extraction with richer source text."
    )
    assert payload["claims"] == []
    assert payload["diagnostics"]["claim_count"] == 0
    assert payload["diagnostics"]["chunk_count"] == 1
    assert payload["diagnostics"]["status"] == "empty"
    assert payload["diagnostics"]["summary"] == (
        "No claims were extracted from the prepared chunks."
    )
    assert payload["diagnostics"]["next_step"] == (
        "Inspect /api/documents/doc-1/chunks and retry extraction with richer source text."
    )





def test_wsgi_document_prepare_accepts_text_alias_payload() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

    case_status, _, case_body = _call_wsgi(
        app,
        method="POST",
        path="/api/cases",
        payload={"title": "Continuity case"},
    )
    case_id = json.loads(case_body)["case"]["case_id"]

    document_status, _, document_body = _call_wsgi(
        app,
        method="POST",
        path=f"/api/cases/{case_id}/documents",
        payload={
            "title": "Restart continuity doc",
            "text": "The bridge reopened after inspection. Traffic resumed after repairs.",
            "source_type": "web_article",
            "source_url": "https://example.test/restart-continuity",
            "content_hash": "sha256:test-text-alias",
        },
    )
    document_payload = json.loads(document_body)
    document_id = document_payload["document_id"]

    prepare_status, _, prepare_body = _call_wsgi(
        app,
        method="POST",
        path=f"/api/documents/{document_id}/prepare",
        payload={"text": "The bridge reopened after inspection. Traffic resumed after repairs."},
    )

    payload = json.loads(prepare_body)
    assert case_status == "201 Created"
    assert document_status == "201 Created"
    assert prepare_status == "200 OK"
    assert payload["status"] == "ready"
    assert payload["resource"] == "document_preparation"
    assert payload["resource_id"] == document_id
    assert payload["next_step"] == f"POST /api/documents/{document_id}/extract-claims"
    assert payload["chunks"][0]["document_id"] == document_id
    assert "Traffic resumed after repairs." in payload["chunks"][0]["raw_text"]

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


def test_case_payload_includes_current_continuity_pack_summary() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

    created_status, _, _ = _call_wsgi(
        app,
        method="POST",
        path="/api/cases",
        payload={"case_id": "case-summary", "title": "Continuity summary case"},
    )
    assert created_status == "201 Created"

    assign_status, _, _ = _call_wsgi(
        app,
        method="POST",
        path="/api/cases/case-summary/continuity-pack",
        payload={
            "artifact_path": "docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md"
        },
    )
    assert assign_status == "200 OK"

    cases_status, _, cases_body = _call_wsgi(app, method="GET", path="/api/cases")
    case_status, _, case_body = _call_wsgi(
        app,
        method="GET",
        path="/api/cases/case-summary",
    )

    assert cases_status == "200 OK"
    cases_payload = json.loads(cases_body)
    assert cases_payload["cases"][0]["continuity_pack"] == {
        "assigned": True,
        "title": "SourceTrace Research Continuity Pack — A1 Reuters South Africa risks",
        "source_artifact_path": "docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md",
    }

    assert case_status == "200 OK"
    case_payload = json.loads(case_body)
    assert case_payload["case"]["continuity_pack"] == {
        "assigned": True,
        "title": "SourceTrace Research Continuity Pack — A1 Reuters South Africa risks",
        "source_artifact_path": "docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md",
    }


def test_wsgi_case_html_shows_document_status_and_next_actions() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

    _call_wsgi(
        app,
        method="POST",
        path="/api/cases",
        payload={
            "case_id": "case-1",
            "title": "Bridge reopening",
            "description": "Track public claims.",
        },
    )
    _call_wsgi(
        app,
        method="POST",
        path="/api/cases/case-1/documents",
        payload={
            "title": "Bridge note",
            "content": "The bridge reopened after inspection.",
        },
    )

    status, headers, body = _call_wsgi(app, method="GET", path="/cases/case-1")

    assert status == "200 OK"
    assert ("Content-Type", "text/html; charset=utf-8") in headers
    assert "<h2>Document status</h2>" in body
    assert "Bridge reopening" in body
    assert "Track public claims." in body
    assert "Bridge note" in body
    assert "Snippet:" in body
    assert "The bridge reopened after inspection." in body
    assert "prepared" in body
    assert "no claims yet" in body
    assert "no credibility yet" in body
    assert "Status:" in body
    assert "Not assessed yet." in body
    assert "POST /api/documents/doc-bridge-note/credibility" in body
    assert "POST /api/documents/doc-bridge-note/extract-claims" in body
    assert "No active continuity pack for this case yet." in body
    assert "POST /api/cases/case-1/continuity-pack" in body
    assert "docs/plans/...continuity-pack..." in body
    assert "Suggested continuity-pack artifacts:" in body
    assert "Assign 2026-05-23-source-trace-research-continuity-pack-cerebroscope.md" in body
    assert "Assign 2026-05-23-source-trace-research-continuity-pack-reuters-a1.md" in body
    assert (
        "/cases/assign-continuity-pack?case_id=case-1&amp;artifact_path="
        "docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md"
    ) in body


def test_case_review_html_renders_active_continuity_pack() -> None:
    delivery = create_default_delivery()
    delivery.create_case(
        CaseCreationRequest(
            case_id="case-cp",
            title="Continuity handoff case",
            description="Track continuity handoff.",
        )
    )
    assigned = delivery.assign_case_continuity_pack(
        "case-cp",
        artifact_path="docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md",
    )
    assert assigned is not None

    html = render_case_review_html(delivery, "case-cp")

    assert "<h2>Continuity pack</h2>" in html
    assert "Reuters A1" in html
    assert "Source artifact:" in html
    assert "<code>docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md</code>" in html
    assert "Open dedicated continuity-pack view" in html
    assert "/continuity-packs/view?artifact_path=docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md" in html
    assert "Render markdown" in html
    assert "/api/continuity-packs/render-markdown?artifact_path=docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md" in html
    assert "Clear active continuity pack" in html
    assert "/cases/clear-continuity-pack?case_id=case-cp" in html
    assert "Replace warning:" in html
    assert "assigning another continuity pack will replace the current active pack for this case." in html
    assert "Suggested replacement continuity-pack artifacts:" in html
    assert "Replace with 2026-05-23-source-trace-research-continuity-pack-cerebroscope.md" in html
    assert "Replace with 2026-05-23-source-trace-research-continuity-pack-reuters-a1.md" in html
    assert "<h3>Potwierdzone</h3>" in html
    assert "<h3>Decision snapshot</h3>" in html



def test_wsgi_document_credibility_response_includes_workflow_envelope() -> None:
    def draft_gateway(evidence_summary: str) -> LlmGenerationResult:
        assert evidence_summary
        return LlmGenerationResult(
            text="Credibility draft available.",
            model="test-model",
            finish_reason="stop",
        )

    delivery = create_default_delivery(
        credibility_draft=draft_gateway,
        credibility_assessed_at=lambda: datetime(2026, 5, 20, 12, 0, tzinfo=UTC),
    )
    delivery.persistence.cases.save_case(
        Case(case_id="case-cred", title="Credibility case", description=None)
    )
    delivery.persistence.documents.save_document(
        Document(
            document_id="doc-cred",
            case_id="case-cred",
            source_type="inline",
            source_url=None,
            publisher=None,
            author=None,
            title="Credibility doc",
            published_at=None,
            retrieved_at=datetime(2026, 5, 20, 11, 0, tzinfo=UTC),
            content_hash="sha256:cred",
            language="en",
        )
    )
    delivery.persistence.documents.save_chunks(
        (
            DocumentChunk(
                chunk_id="doc-cred:chunk-1",
                case_id="case-cred",
                document_id="doc-cred",
                raw_text="This launch post claims a product is number one in Europe.",
                start_char=0,
                end_char=58,
                chunk_index=0,
                position_reference="p1",
            ),
        )
    )
    app = SourceTraceWSGIApp(delivery=delivery)

    status, _, body = _call_wsgi(
        app,
        method="POST",
        path="/api/documents/doc-cred/credibility",
        payload={},
    )

    payload = json.loads(body)
    assert status == "200 OK"
    assert payload["status"] == "ready"
    assert payload["resource"] == "document_credibility"
    assert payload["resource_id"] == "doc-cred"
    assert payload["document_id"] == "doc-cred"
    assert payload["next_step"] == "GET /api/documents/doc-cred/credibility"
    assert payload["credibility_assessment"]["document_id"] == "doc-cred"
    assert payload["credibility_assessment"]["notes"] == "Credibility draft available."



def test_wsgi_case_html_returns_404_for_missing_case() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

    status, headers, body = _call_wsgi(
        app,
        method="GET",
        path="/cases/missing-case",
    )

    html = body
    assert status == "404 Not Found"
    assert ("Content-Type", "text/html; charset=utf-8") in headers
    assert "Case not found" in html
    assert "missing-case" in html
    assert "Case None" not in html



def test_wsgi_case_html_shows_api_aligned_verdict_and_evidence_links() -> None:
    from sourcetrace.domain import Case

    document = Document(
        document_id="doc-1",
        case_id="case-1",
        source_type="url",
        source_url="https://example.test/bridge",
        publisher=None,
        author=None,
        title="Bridge update",
        published_at=None,
        retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
        content_hash="sha256:abc123",
        language="en",
    )
    chunk = DocumentChunk(
        chunk_id="doc-1:chunk-1",
        case_id="case-1",
        document_id="doc-1",
        raw_text="The bridge reopened after inspection.",
        start_char=0,
        end_char=37,
        chunk_index=0,
        position_reference="p1",
    )
    claim = Claim(
        claim_id="case-1:claim-1",
        case_id="case-1",
        document_id="doc-1",
        chunk_id="doc-1:chunk-1",
        exact_text="The bridge reopened after inspection.",
        source_span_reference="p1",
        system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
    )
    evidence = ClaimEvidenceLink(
        claim_id="case-1:claim-1",
        document_id="doc-1",
        chunk_id="doc-1:chunk-1",
        evidence_rank=1,
        evidence_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale="Initial extraction link.",
        snippet="The bridge reopened after inspection.",
        score=None,
    )
    delivery = create_default_delivery()
    delivery.persistence.cases.save_case(
        Case(case_id="case-1", title="Bridge case", description=None)
    )
    delivery.persistence.documents.save_document(document)
    delivery.persistence.documents.save_chunks((chunk,))
    delivery.persistence.claims.save_claims((claim,))
    delivery.persistence.documents.save_credibility_assessment(
        __import__("sourcetrace.domain", fromlist=["DocumentCredibilityAssessment"]).DocumentCredibilityAssessment(
            assessment_id="credibility-doc-1",
            document_id="doc-1",
            source_reliability=__import__("sourcetrace.domain.types", fromlist=["CredibilityBand"]).CredibilityBand.UNKNOWN,
            information_credibility=__import__("sourcetrace.domain.types", fromlist=["CredibilityBand"]).CredibilityBand.UNKNOWN,
            source_reliability_factors=(),
            information_credibility_factors=(),
            provenance_distance=__import__("sourcetrace.domain.types", fromlist=["ProvenanceDistance"]).ProvenanceDistance.UNKNOWN,
            method="llm_draft_v1",
            notes="Summary: Lead only; provenance remains weak.\nStrengths: Publisher is identified\nConcerns: No underlying dataset is linked\nVerification checks: Confirm with the original ministry release",
            summary="Lead only; provenance remains weak.",
            strengths=("Publisher is identified",),
            concerns=("No underlying dataset is linked",),
            verification_checks=("Confirm with the original ministry release",),
            assessed_by="system",
            assessed_at=datetime(2026, 5, 18, 0, 10, tzinfo=UTC),
            override=False,
        )
    )
    app = SourceTraceWSGIApp(delivery=delivery)

    status, headers, body = _call_wsgi(
        app,
        method="GET",
        path="/cases/case-1",
    )

    html = body
    assert status == "200 OK"
    assert ("Content-Type", "text/html; charset=utf-8") in headers
    assert "insufficient_evidence" in html
    assert "/api/claims/case-1:claim-1" in html
    assert "/api/claims/case-1:claim-1/evidence" in html
    assert "/api/claims/case-1:claim-1/verification" in html
    assert "Summary:" in html
    assert "Lead only; provenance remains weak." in html
    assert "Strengths:" in html
    assert "Publisher is identified" in html
    assert "Concerns:" in html
    assert "No underlying dataset is linked" in html
    assert "Verification checks:" in html
    assert "Confirm with the original ministry release" in html




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
    ready_payload = json.loads(ready_body)
    assert ready_payload["checks"]["delivery"] is True
    assert ready_payload["checks"]["continuity_pack"] is True
    assert ready_payload["checks"]["continuity_pack_persistence"] is False
    assert ready_payload["diagnostics"]["continuity_pack_persistence"] == {
        "enabled": False,
        "backend": "InMemoryCaseRepository",
        "root_dir": None,
    }
    assert runtime_status == "200 OK"
    runtime_payload = json.loads(runtime_body)
    assert runtime_payload["runtime"]["entrypoint"] == "wsgi"
    assert runtime_payload["runtime"]["continuity_pack"] == "enabled"
    assert runtime_payload["runtime"]["continuity_pack_persistence"] == {
        "enabled": False,
        "backend": "InMemoryCaseRepository",
        "root_dir": None,
    }
    assert capabilities_status == "200 OK"
    capabilities_payload = json.loads(capabilities_body)
    assert "/api/cases/{case_id}/documents" in capabilities_payload["routes"]["product"]
    assert "/api/dev/documents" in capabilities_payload["routes"]["dev"]
    assert capabilities_payload["capabilities"]["continuity_packs"] == [
        "assemble_preview",
        "assemble_from_artifact",
        "render_markdown",
    ]


def test_wsgi_operational_endpoints_report_file_backed_continuity_pack_persistence(
    tmp_path,
) -> None:
    delivery = create_default_delivery(continuity_pack_root_dir=tmp_path)
    app = SourceTraceWSGIApp(delivery=delivery)

    ready_status, _, ready_body = _call_wsgi(app, method="GET", path="/api/ready")
    runtime_status, _, runtime_body = _call_wsgi(app, method="GET", path="/api/runtime")

    assert ready_status == "200 OK"
    ready_payload = json.loads(ready_body)
    assert ready_payload["checks"]["continuity_pack_persistence"] is True
    assert ready_payload["diagnostics"]["continuity_pack_persistence"] == {
        "enabled": True,
        "backend": "FileBackedCaseRepository",
        "root_dir": str(tmp_path),
    }

    assert runtime_status == "200 OK"
    runtime_payload = json.loads(runtime_body)
    assert runtime_payload["runtime"]["continuity_pack_persistence"] == {
        "enabled": True,
        "backend": "FileBackedCaseRepository",
        "root_dir": str(tmp_path),
    }


def test_delivery_can_assemble_continuity_pack_preview() -> None:
    delivery = create_default_delivery()

    inspection = delivery.inspect_continuity_pack(
        ContinuityPackRequest(
            title="Reuters A1 continuity pack",
            source_artifact_path="docs/plans/2026-05-21-observation-a1-reuters-south-africa-risks.md",
            confirmed=("Evidence exists.", "The observation note is decision-relevant."),
            assumptions=("Decision owner is still the same.",),
            to_verify=("Whether broader rollout is justified.",),
            recommended_next_test=("Run one bounded follow-up on another source class.",),
            decision_snapshot=("Ready for bounded follow-up.",),
        )
    )

    assert inspection is not None
    assert inspection.title == "Reuters A1 continuity pack"
    assert inspection.source_artifact_path.endswith("reuters-south-africa-risks.md")
    assert inspection.sections["Potwierdzone"] == (
        "Evidence exists.",
        "The observation note is decision-relevant.",
    )
    assert inspection.sections["Recommended next test"] == (
        "Run one bounded follow-up on another source class.",
    )
    assert inspection.decision_snapshot == ("Ready for bounded follow-up.",)


def test_delivery_can_build_continuity_pack_from_artifact() -> None:
    delivery = create_default_delivery()

    outcome = delivery.build_continuity_pack_from_artifact(
        "docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md"
    )

    assert outcome is not None
    assert outcome.continuity_pack.title
    assert outcome.continuity_pack.source_artifact_path.endswith(
        "2026-05-23-source-trace-research-continuity-pack-reuters-a1.md"
    )
    assert outcome.continuity_pack.confirmed
    assert outcome.continuity_pack.recommended_next_test


def test_delivery_can_render_continuity_pack_markdown_from_artifact() -> None:
    delivery = create_default_delivery()

    markdown = delivery.render_continuity_pack_markdown_from_artifact(
        "docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md"
    )

    assert markdown is not None
    assert markdown.startswith("# ")
    assert "## Potwierdzone" in markdown
    assert "## Recommended next test" in markdown


def test_wsgi_can_assemble_continuity_pack_preview() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

    status, _, body = _call_wsgi(
        app,
        method="POST",
        path="/api/continuity-packs/assemble-preview",
        payload={
            "title": "Reuters A1 continuity pack",
            "source_artifact_path": "docs/plans/2026-05-21-observation-a1-reuters-south-africa-risks.md",
            "confirmed": ["Evidence exists.", "The observation note is decision-relevant."],
            "assumptions": ["Decision owner is still the same."],
            "to_verify": ["Whether broader rollout is justified."],
            "recommended_next_test": ["Run one bounded follow-up on another source class."],
            "decision_snapshot": ["Ready for bounded follow-up."],
        },
    )

    assert status == "200 OK"
    payload = json.loads(body)
    assert payload["resource"] == "continuity_pack"
    assert payload["resource_id"].endswith("reuters-south-africa-risks.md")
    assert payload["continuity_pack"]["title"] == "Reuters A1 continuity pack"
    assert payload["continuity_pack"]["confirmed"] == [
        "Evidence exists.",
        "The observation note is decision-relevant.",
    ]
    assert payload["continuity_pack"]["recommended_next_test"] == [
        "Run one bounded follow-up on another source class.",
    ]


def test_wsgi_rejects_invalid_continuity_pack_preview_payload() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

    status, _, body = _call_wsgi(
        app,
        method="POST",
        path="/api/continuity-packs/assemble-preview",
        payload={
            "title": "",
            "source_artifact_path": "docs/plans/example.md",
            "confirmed": "not-a-list",
            "assumptions": [],
            "to_verify": [],
            "recommended_next_test": [],
        },
    )

    assert status == "400 Bad Request"
    payload = json.loads(body)
    assert payload["status"] == "invalid_request"


def test_wsgi_can_assemble_continuity_pack_from_artifact() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

    status, _, body = _call_wsgi(
        app,
        method="POST",
        path="/api/continuity-packs/assemble-from-artifact",
        payload={
            "artifact_path": "docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md"
        },
    )

    assert status == "200 OK"
    payload = json.loads(body)
    assert payload["resource"] == "continuity_pack"
    assert payload["continuity_pack"]["confirmed"]
    assert payload["continuity_pack"]["recommended_next_test"]


def test_wsgi_rejects_missing_continuity_pack_artifact_path() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

    status, _, body = _call_wsgi(
        app,
        method="POST",
        path="/api/continuity-packs/assemble-from-artifact",
        payload={"artifact_path": "docs/plans/missing-continuity-pack.md"},
    )

    assert status == "400 Bad Request"
    payload = json.loads(body)
    assert payload["status"] == "invalid_request"
    assert payload["error"] == "artifact_path not found: docs/plans/missing-continuity-pack.md"


def test_wsgi_rejects_incomplete_continuity_pack_artifact() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

    status, _, body = _call_wsgi(
        app,
        method="POST",
        path="/api/continuity-packs/assemble-from-artifact",
        payload={"artifact_path": "docs/plans/2026-05-23-broken-continuity-pack.md"},
    )

    assert status == "400 Bad Request"
    payload = json.loads(body)
    assert payload["status"] == "invalid_request"
    assert payload["error"] == (
        "artifact_path is missing required continuity-pack sections with bullet items: "
        "Recommended next test"
    )


def test_wsgi_can_render_continuity_pack_markdown_from_artifact() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

    status, headers, body = _call_wsgi(
        app,
        method="POST",
        path="/api/continuity-packs/render-markdown",
        payload={
            "artifact_path": "docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md"
        },
    )

    assert status == "200 OK"
    assert ("Content-Type", "text/markdown; charset=utf-8") in headers
    assert body.startswith("# ")
    assert "## Potwierdzone" in body
    assert "## Recommended next test" in body


def test_wsgi_rejects_artifact_outside_repo_for_continuity_pack_render() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

    status, _, body = _call_wsgi(
        app,
        method="POST",
        path="/api/continuity-packs/render-markdown",
        payload={"artifact_path": "../outside.md"},
    )

    assert status == "400 Bad Request"
    payload = json.loads(body)
    assert payload["status"] == "invalid_request"
    assert payload["error"] == "artifact_path must stay inside the repo root."


def test_wsgi_can_render_continuity_pack_html_view() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

    status, headers, body = _call_wsgi(
        app,
        method="GET",
        path="/continuity-packs/view",
        query_string=(
            "artifact_path="
            "docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md"
        ),
    )

    assert status == "200 OK"
    assert ("Content-Type", "text/html; charset=utf-8") in headers
    assert "<h1>" in body
    assert "Source artifact:" in body
    assert "<h2>Potwierdzone</h2>" in body
    assert "<h2>Recommended next test</h2>" in body


def test_wsgi_rejects_continuity_pack_html_view_without_artifact_path() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

    status, headers, body = _call_wsgi(
        app,
        method="GET",
        path="/continuity-packs/view",
    )

    assert status == "400 Bad Request"
    assert ("Content-Type", "application/json; charset=utf-8") in headers
    payload = json.loads(body)
    assert payload["status"] == "invalid_request"
    assert payload["error"] == "artifact_path query parameter is required."


def test_wsgi_can_assign_case_continuity_pack_from_query_and_redirect() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

    created_status, _, _ = _call_wsgi(
        app,
        method="POST",
        path="/api/cases",
        payload={"case_id": "case-assign", "title": "Assign continuity case"},
    )
    assert created_status == "201 Created"

    status, headers, body = _call_wsgi(
        app,
        method="GET",
        path="/cases/assign-continuity-pack",
        query_string=(
            "case_id=case-assign&artifact_path="
            "docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md"
        ),
    )

    assert status == "303 See Other"
    assert ("Location", "/cases/case-assign") in headers
    assert body == ""

    get_status, _, get_body = _call_wsgi(
        app,
        method="GET",
        path="/api/cases/case-assign/continuity-pack",
    )
    assert get_status == "200 OK"
    payload = json.loads(get_body)
    assert payload["continuity_pack"]["source_artifact_path"].endswith("reuters-a1.md")


def test_wsgi_assign_case_continuity_pack_from_query_missing_case_returns_html_404() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

    status, headers, body = _call_wsgi(
        app,
        method="GET",
        path="/cases/assign-continuity-pack",
        query_string=(
            "case_id=missing-case&artifact_path="
            "docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md"
        ),
    )

    assert status == "404 Not Found"
    assert ("Content-Type", "text/html; charset=utf-8") in headers
    assert "Case not found" in body
    assert "Cannot assign continuity pack to missing case: missing-case" in body


def test_wsgi_can_clear_case_continuity_pack_via_api() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

    created_status, _, _ = _call_wsgi(
        app,
        method="POST",
        path="/api/cases",
        payload={"case_id": "case-clear", "title": "Clear continuity case"},
    )
    assert created_status == "201 Created"

    assign_status, _, _ = _call_wsgi(
        app,
        method="POST",
        path="/api/cases/case-clear/continuity-pack",
        payload={
            "artifact_path": "docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md"
        },
    )
    assert assign_status == "200 OK"

    clear_status, _, clear_body = _call_wsgi(
        app,
        method="DELETE",
        path="/api/cases/case-clear/continuity-pack",
    )
    assert clear_status == "200 OK"
    clear_payload = json.loads(clear_body)
    assert clear_payload["summary"] == "Active continuity pack cleared."

    get_status, _, get_body = _call_wsgi(
        app,
        method="GET",
        path="/api/cases/case-clear/continuity-pack",
    )
    assert get_status == "404 Not Found"
    get_payload = json.loads(get_body)
    assert get_payload["error"] == "continuity_pack_not_found"


def test_wsgi_can_clear_case_continuity_pack_from_query_and_redirect() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

    created_status, _, _ = _call_wsgi(
        app,
        method="POST",
        path="/api/cases",
        payload={"case_id": "case-clear-html", "title": "Clear continuity case"},
    )
    assert created_status == "201 Created"

    assign_status, _, _ = _call_wsgi(
        app,
        method="POST",
        path="/api/cases/case-clear-html/continuity-pack",
        payload={
            "artifact_path": "docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md"
        },
    )
    assert assign_status == "200 OK"

    clear_status, headers, body = _call_wsgi(
        app,
        method="GET",
        path="/cases/clear-continuity-pack",
        query_string="case_id=case-clear-html",
    )
    assert clear_status == "303 See Other"
    assert ("Location", "/cases/case-clear-html") in headers
    assert body == ""

    get_status, _, get_body = _call_wsgi(
        app,
        method="GET",
        path="/api/cases/case-clear-html/continuity-pack",
    )
    assert get_status == "404 Not Found"
    get_payload = json.loads(get_body)
    assert get_payload["error"] == "continuity_pack_not_found"


def test_wsgi_case_continuity_pack_missing_for_existing_case() -> None:
    app = SourceTraceWSGIApp(delivery=create_default_delivery())

    created_status, _, _ = _call_wsgi(
        app,
        method="POST",
        path="/api/cases",
        payload={"case_id": "case-2", "title": "Empty continuity case"},
    )
    assert created_status == "201 Created"

    status, _, body = _call_wsgi(
        app,
        method="GET",
        path="/api/cases/case-2/continuity-pack",
    )

    assert status == "404 Not Found"
    payload = json.loads(body)
    assert payload["error"] == "continuity_pack_not_found"


def test_file_backed_case_repository_persists_active_continuity_pack(
    tmp_path,
) -> None:
    continuity_root = tmp_path / "state"
    repository = FileBackedCaseRepository(continuity_root)
    repository.save_case(Case(case_id="case-fs", title="File-backed case", description=None))
    persistence = create_in_memory_persistence()
    persistence = persistence.__class__(
        cases=repository,
        documents=persistence.documents,
        claims=persistence.claims,
    )
    delivery = create_default_delivery(persistence=persistence)

    assigned = delivery.assign_case_continuity_pack(
        "case-fs",
        artifact_path="docs/plans/2026-05-23-source-trace-research-continuity-pack-reuters-a1.md",
    )
    assert assigned is not None

    reloaded_repository = FileBackedCaseRepository(continuity_root)
    reloaded_repository.save_case(
        Case(case_id="case-fs", title="File-backed case", description=None)
    )
    reloaded_persistence = create_in_memory_persistence()
    reloaded_persistence = reloaded_persistence.__class__(
        cases=reloaded_repository,
        documents=reloaded_persistence.documents,
        claims=reloaded_persistence.claims,
    )
    reloaded_delivery = create_default_delivery(persistence=reloaded_persistence)

    persisted = reloaded_delivery.get_case_continuity_pack("case-fs")
    assert persisted is not None
    assert persisted.continuity_pack == assigned.continuity_pack



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
    query_string: str = "",
) -> tuple[str, list[tuple[str, str]], str]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else b""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
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
