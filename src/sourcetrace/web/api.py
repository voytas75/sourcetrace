"""Pure-stdlib WSGI API for the minimal delivery surface."""

import json
import traceback
from os import environ
from collections.abc import Callable, Iterable
from contextlib import suppress
from dataclasses import dataclass
from typing import Any
from wsgiref.simple_server import WSGIServer, make_server

from sourcetrace.application import (
    ContinuityPackRequest,
    DocumentPreparationOutcome,
    DocumentPreparationRequest,
    build_continuity_pack_request_from_artifact,
    render_continuity_pack_markdown,
)
from sourcetrace.web.delivery import (
    SourceTraceDelivery,
    VerificationDeliveryRequest,
    case_creation_request_from_payload,
    case_to_payload,
    chunk_to_payload,
    claim_extraction_outcome_to_payload,
    claim_from_payload,
    continuity_pack_outcome_to_payload,
    continuity_pack_read_payload,
    create_default_delivery,
    credibility_assessment_response_payload,
    document_credibility_assessment_to_payload,
    document_from_payload,
    document_preparation_outcome_to_payload,
    document_to_payload,
    render_case_review_html,
    render_continuity_pack_html,
    render_report_html,
    render_report_markdown,
    report_outcome_to_payload,
    review_decision_from_payload,
    review_decision_to_payload,
    evidence_link_to_payload,
    claim_to_payload,
    verification_inspection_to_payload,
    verification_outcome_to_payload,
    _escape_html,
)
from sourcetrace.application import SourceIngestionRequest
from sourcetrace.domain.research import CompiledResearchArtifact, CompiledResearchArtifactLint, ResearchJob, ResearchProgressEvent, ResearchResultArtifact, ResearchSettings


StartResponse = Callable[[str, list[tuple[str, str]]], None]
WsgiEnviron = dict[str, Any]


def _debug_api_errors_enabled() -> bool:
    return environ.get("SOURCETRACE_DEBUG_API_ERRORS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


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
        except Exception as exc:
            if _debug_api_errors_enabled():
                print(
                    "[sourcetrace.api-error] "
                    f"method={method} path={path} "
                    f"error_type={type(exc).__name__} error={exc}",
                    flush=True,
                )
                traceback.print_exc()
            return _json_response(
                start_response,
                "500 Internal Server Error",
                {"error": "internal_server_error", "status": "error"},
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
        if method == "GET" and path == "/research":
            return self._render_research_console(start_response)
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
            if parts[3] == "continuity-pack":
                if method == "GET":
                    return self._get_case_continuity_pack(case_id, start_response)
                if method == "POST":
                    return self._assign_case_continuity_pack(
                        case_id,
                        environ,
                        start_response,
                    )
                if method == "DELETE":
                    return self._clear_case_continuity_pack(case_id, start_response)
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
        if parts[:2] == ("api", "research"):
            if len(parts) == 3 and parts[2] == "start" and method == "POST":
                return self._start_research_job(environ, start_response)
            if len(parts) == 3 and parts[2] == "jobs" and method == "GET":
                return self._list_research_jobs(environ, start_response)
            if len(parts) == 4 and parts[2] == "status" and method == "GET":
                return self._get_research_status(parts[3], start_response)
            if len(parts) == 4 and parts[2] == "stream" and method == "GET":
                return self._stream_research_progress(parts[3], start_response)
            if len(parts) == 4 and parts[2] == "result" and parts[3].endswith('.html') and method == "GET":
                return self._render_research_result_html(path, start_response)
            if len(parts) == 4 and parts[2] == "result" and method == "GET":
                return self._get_research_result(parts[3], start_response)
            if len(parts) == 4 and parts[2] == "run" and method == "POST":
                return self._run_research_job(parts[3], start_response)
            if len(parts) == 4 and parts[2] == "cancel" and method == "POST":
                return self._cancel_research_job(parts[3], start_response)
            if len(parts) == 5 and parts[2] == "compiled" and parts[4] == "lint" and method == "GET":
                return self._get_compiled_research_artifact_lint(parts[3], start_response)
            if len(parts) == 4 and parts[2] == "compiled" and method == "GET":
                return self._get_compiled_research_artifact(parts[3], start_response)
            if len(parts) == 3 and parts[2] == "compiled" and method == "GET":
                return self._list_compiled_research_artifacts(environ, start_response)
        if method == "POST" and path == "/api/verify":
            return self._verify_claim(environ, start_response)
        if method == "POST" and path == "/api/dev/documents":
            return self._seed_document(environ, start_response)
        if method == "POST" and path == "/api/reviews":
            return self._record_review(environ, start_response)
        if method == "POST" and path == "/api/continuity-packs/assemble-preview":
            return self._assemble_continuity_pack_preview(environ, start_response)
        if method == "POST" and path == "/api/continuity-packs/assemble-from-artifact":
            return self._assemble_continuity_pack_from_artifact(environ, start_response)
        if method == "POST" and path == "/api/continuity-packs/render-markdown":
            return self._render_continuity_pack_markdown_preview(environ, start_response)
        if method == "GET" and path.startswith("/api/reports/"):
            return self._render_report(path, start_response)
        if method == "GET" and path == "/continuity-packs/view":
            return self._render_continuity_pack_view(environ, start_response)
        if method == "GET" and path == "/cases/assign-continuity-pack":
            return self._assign_case_continuity_pack_from_query(environ, start_response)
        if method == "GET" and path == "/cases/clear-continuity-pack":
            return self._clear_case_continuity_pack_from_query(environ, start_response)
        if method == "GET" and path.startswith("/cases/"):
            case_id = path.removeprefix("/cases/").strip("/")
            case = self.delivery.get_case(case_id)
            status = "200 OK" if case is not None else "404 Not Found"
            return _html_response(
                start_response,
                status,
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

    def _render_research_console(
        self,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        return _html_response(
            start_response,
            "200 OK",
            _render_research_console_html(),
        )

    def _start_research_job(
        self,
        environ: WsgiEnviron,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        payload = _read_json(environ)
        owner_id = _required_str(payload, "owner_id").strip().lower()
        query = _required_str(payload, "query")
        outcome = self.delivery.start_research_job(owner_id=owner_id, query=query)
        if outcome is None:
            return _json_response(start_response, "503 Service Unavailable", {"error": "research_unavailable", "status": "unavailable"})
        return _json_response(
            start_response,
            "201 Created",
            {
                "status": "accepted",
                "job": _research_job_to_payload(outcome.job),
            },
        )

    def _list_research_jobs(
        self,
        environ: WsgiEnviron,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        owner_id = _required_query_param(environ, "owner_id").strip().lower()
        outcome = self.delivery.list_research_jobs(owner_id)
        if outcome is None:
            return _json_response(start_response, "503 Service Unavailable", {"error": "research_unavailable", "status": "unavailable"})
        return _json_response(
            start_response,
            "200 OK",
            {"owner_id": owner_id, "jobs": [_research_job_to_payload(job) for job in outcome.jobs]},
        )

    def _get_research_status(
        self,
        job_id: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        outcome = self.delivery.get_research_job_status(job_id)
        if outcome is None:
            return _missing_response(start_response, "research_job", job_id)
        return _json_response(
            start_response,
            "200 OK",
            {
                "job": _research_job_to_payload(outcome.job),
                "progress": [_research_progress_to_payload(event) for event in outcome.progress],
            },
        )

    def _stream_research_progress(
        self,
        job_id: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        outcome = self.delivery.get_research_job_status(job_id)
        if outcome is None:
            return _missing_response(start_response, "research_job", job_id)
        events = [_research_progress_to_payload(event) for event in outcome.progress]
        final_payload = {
            "job": _research_job_to_payload(outcome.job),
            "final": outcome.job.status.value in {"done", "error", "cancelled"},
        }
        return _sse_response(
            start_response,
            events=events,
            final_payload=final_payload,
        )

    def _get_research_result(
        self,
        job_id: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        outcome = self.delivery.get_research_result(job_id)
        if outcome is None:
            return _missing_response(start_response, "research_job", job_id)
        if outcome.result is None:
            return _json_response(
                start_response,
                "202 Accepted",
                {"status": "pending", "job": _research_job_to_payload(outcome.job), "result": None},
            )
        return _json_response(
            start_response,
            "200 OK",
            {"status": "ready", "job": _research_job_to_payload(outcome.job), "result": _research_result_to_payload(outcome.result)},
        )

    def _run_research_job(
        self,
        job_id: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        result = self.delivery.run_research_job(job_id)
        status_outcome = self.delivery.get_research_job_status(job_id)
        if status_outcome is None:
            return _missing_response(start_response, "research_job", job_id)
        return _json_response(
            start_response,
            "200 OK",
            {
                "job": _research_job_to_payload(status_outcome.job),
                "progress": [_research_progress_to_payload(event) for event in status_outcome.progress],
                "result": _research_result_to_payload(result) if result is not None else None,
            },
        )

    def _cancel_research_job(
        self,
        job_id: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        job = self.delivery.cancel_research_job(job_id)
        if job is None:
            return _missing_response(start_response, "research_job", job_id)
        return _json_response(start_response, "200 OK", {"job": _research_job_to_payload(job)})

    def _get_compiled_research_artifact(
        self,
        artifact_id: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        artifact = self.delivery.research.persistence.compiled.get_artifact(artifact_id)
        if artifact is None:
            return _missing_response(start_response, "compiled_research_artifact", artifact_id)
        return _json_response(
            start_response,
            "200 OK",
            {"status": "ready", "artifact": _compiled_research_artifact_to_payload(artifact)},
        )

    def _list_compiled_research_artifacts(
        self,
        environ: WsgiEnviron,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        owner_id = _required_query_param(environ, "owner_id").strip().lower()
        artifacts = self.delivery.research.persistence.compiled.list_artifacts_for_owner(owner_id)
        return _json_response(
            start_response,
            "200 OK",
            {"owner_id": owner_id, "artifacts": [_compiled_research_artifact_to_payload(item) for item in artifacts]},
        )

    def _get_compiled_research_artifact_lint(
        self,
        artifact_id: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        lint = self.delivery.research.persistence.compiled_lint.get_lint_for_artifact(artifact_id)
        if lint is None:
            return _missing_response(start_response, "compiled_research_artifact_lint", artifact_id)
        return _json_response(
            start_response,
            "200 OK",
            {"status": "ready", "lint": _compiled_research_artifact_lint_to_payload(lint)},
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
        continuity_pack = self.delivery.get_case_continuity_pack(outcome.case.case_id)
        latest_previous = self.delivery.get_latest_previous_case_continuity_pack(
            outcome.case.case_id
        )
        case_payload = case_to_payload(
            outcome.case,
            continuity_pack=continuity_pack,
            latest_previous_continuity_pack=latest_previous,
        )
        return _json_response(
            start_response,
            "201 Created",
            {
                "status": "ready",
                "summary": "Case created.",
                "next_step": f"POST /api/cases/{case_payload['case_id']}/documents",
                "resource": "case",
                "resource_id": case_payload["case_id"],
                "case": case_payload,
                "case_id": case_payload["case_id"],
            },
        )

    def _list_cases(
        self,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        return _json_response(
            start_response,
            "200 OK",
            {
                "cases": [
                    case_to_payload(
                        case,
                        continuity_pack=self.delivery.get_case_continuity_pack(case.case_id),
                        latest_previous_continuity_pack=(
                            self.delivery.get_latest_previous_case_continuity_pack(case.case_id)
                        ),
                    )
                    for case in self.delivery.list_cases()
                ]
            },
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
            {
                "case": case_to_payload(
                    case,
                    continuity_pack=self.delivery.get_case_continuity_pack(case.case_id),
                    latest_previous_continuity_pack=(
                        self.delivery.get_latest_previous_case_continuity_pack(case.case_id)
                    ),
                )
            },
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
        inline_content = _optional_str(payload.get("content")) or _optional_str(payload.get("text"))
        if inline_content:
            self.delivery.prepare_document(
                DocumentPreparationRequest(
                    case_id=case_id,
                    document_id=document.document_id,
                    chunking_method=_optional_str(payload.get("chunking_method")),
                ),
                inline_content,
            )
        document_payload = document_to_payload(outcome.document)
        return _json_response(
            start_response,
            "201 Created",
            {
                "status": "ready",
                "summary": "Document attached to case.",
                "next_step": f"POST /api/documents/{document_payload['document_id']}/prepare",
                "resource": "document",
                "resource_id": document_payload["document_id"],
                "document": document_payload,
                "document_id": document_payload["document_id"],
            },
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
        raw_text = str(
            payload.get("raw_text")
            or payload.get("content")
            or payload.get("text")
            or document.inline_content
            or ""
        )
        if not raw_text:
            existing_chunks = self.delivery.list_chunks_for_document(document_id)
            if existing_chunks:
                outcome = DocumentPreparationOutcome(
                    request=DocumentPreparationRequest(
                        case_id=document.case_id,
                        document_id=document.document_id,
                        chunking_method=_optional_str(payload.get("chunking_method")),
                    ),
                    document=document,
                    chunks=existing_chunks,
                )
                return _json_response(
                    start_response,
                    "200 OK",
                    document_preparation_outcome_to_payload(outcome),
                )
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
        document = self.delivery.get_document(document_id)
        if document is None:
            return _missing_response(start_response, "document", document_id)
        if not self.delivery.list_chunks_for_document(document_id):
            inline_content = document.inline_content or ""
            if inline_content.strip():
                self.delivery.prepare_document(
                    DocumentPreparationRequest(
                        case_id=document.case_id,
                        document_id=document.document_id,
                        chunking_method=None,
                    ),
                    inline_content,
                )
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

    def _assign_case_continuity_pack(
        self,
        case_id: str,
        environ: WsgiEnviron,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        payload = _read_json(environ)
        outcome = self.delivery.assign_case_continuity_pack(
            case_id,
            artifact_path=_required_str(payload, "artifact_path"),
            title=_optional_str(payload.get("title")),
        )
        if outcome is None:
            return _missing_response(start_response, "case", case_id)
        return _json_response(
            start_response,
            "200 OK",
            continuity_pack_outcome_to_payload(outcome),
        )

    def _assign_case_continuity_pack_from_query(
        self,
        environ: WsgiEnviron,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        case_id = _required_query_param(environ, "case_id")
        artifact_path = _required_query_param(environ, "artifact_path")
        title = _optional_query_param(environ, "title")
        outcome = self.delivery.assign_case_continuity_pack(
            case_id,
            artifact_path=artifact_path,
            title=title,
        )
        if outcome is None:
            return _html_response(
                start_response,
                "404 Not Found",
                _render_error_html(
                    title="Case not found",
                    message=f"Cannot assign continuity pack to missing case: {case_id}",
                ),
            )
        return _redirect_response(
            start_response,
            f"/cases/{case_id}",
        )

    def _get_case_continuity_pack(
        self,
        case_id: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        case = self.delivery.get_case(case_id)
        if case is None:
            return _missing_response(start_response, "case", case_id)
        outcome = self.delivery.get_case_continuity_pack(case_id)
        latest_previous = self.delivery.get_latest_previous_case_continuity_pack(case_id)
        if outcome is None and latest_previous is None:
            return _json_response(
                start_response,
                "200 OK",
                continuity_pack_read_payload(
                    case_id=case_id,
                    active=None,
                    latest_previous=None,
                ),
            )
        return _json_response(
            start_response,
            "200 OK",
            continuity_pack_read_payload(
                case_id=case_id,
                active=outcome,
                latest_previous=latest_previous,
            ),
        )

    def _clear_case_continuity_pack(
        self,
        case_id: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        case = self.delivery.get_case(case_id)
        if case is None:
            return _missing_response(start_response, "case", case_id)
        self.delivery.clear_case_continuity_pack(case_id)
        return _json_response(
            start_response,
            "200 OK",
            {
                "status": "ready",
                "resource": "continuity_pack",
                "resource_id": case_id,
                "case_id": case_id,
                "summary": "Active continuity pack cleared.",
                "next_step": f"GET /cases/{case_id}",
            },
        )

    def _clear_case_continuity_pack_from_query(
        self,
        environ: WsgiEnviron,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        case_id = _required_query_param(environ, "case_id")
        case = self.delivery.get_case(case_id)
        if case is None:
            return _html_response(
                start_response,
                "404 Not Found",
                _render_error_html(
                    title="Case not found",
                    message=f"Cannot clear continuity pack for missing case: {case_id}",
                ),
            )
        self.delivery.clear_case_continuity_pack(case_id)
        return _redirect_response(start_response, f"/cases/{case_id}")

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
        if review_decision is None:
            return _json_response(
                start_response,
                "404 Not Found",
                {"error": "claim_not_found", "status": "missing"},
            )
        return _json_response(
            start_response,
            "200 OK",
            {"review_decision": review_decision_to_payload(review_decision)},
        )

    def _assemble_continuity_pack_preview(
        self,
        environ: WsgiEnviron,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        payload = _read_json(environ)
        outcome = self.delivery.assemble_continuity_pack(
            ContinuityPackRequest(
                title=_required_str(payload, "title"),
                source_artifact_path=_required_str(payload, "source_artifact_path"),
                confirmed=_string_tuple(payload.get("confirmed"), field_name="confirmed"),
                assumptions=_string_tuple(payload.get("assumptions"), field_name="assumptions"),
                to_verify=_string_tuple(payload.get("to_verify"), field_name="to_verify"),
                recommended_next_test=_string_tuple(
                    payload.get("recommended_next_test"),
                    field_name="recommended_next_test",
                ),
                decision_snapshot=_string_tuple(
                    payload.get("decision_snapshot", ()),
                    field_name="decision_snapshot",
                ),
                verification_diagnostics=_string_tuple(
                    payload.get("verification_diagnostics", ()),
                    field_name="verification_diagnostics",
                ),
            )
        )
        if outcome is None:
            return _json_response(
                start_response,
                "501 Not Implemented",
                {
                    "error": "continuity_pack_not_available",
                    "status": "unsupported",
                },
            )
        return _json_response(
            start_response,
            "200 OK",
            continuity_pack_outcome_to_payload(outcome),
        )

    def _assemble_continuity_pack_from_artifact(
        self,
        environ: WsgiEnviron,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        payload = _read_json(environ)
        outcome = self.delivery.build_continuity_pack_from_artifact(
            _required_str(payload, "artifact_path"),
            title=_optional_str(payload.get("title")),
        )
        if outcome is None:
            return _json_response(
                start_response,
                "501 Not Implemented",
                {
                    "error": "continuity_pack_not_available",
                    "status": "unsupported",
                },
            )
        return _json_response(
            start_response,
            "200 OK",
            continuity_pack_outcome_to_payload(outcome),
        )

    def _render_continuity_pack_markdown_preview(
        self,
        environ: WsgiEnviron,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        payload = _read_json(environ)
        artifact_path = _optional_str(payload.get("artifact_path"))
        if artifact_path:
            markdown = self.delivery.render_continuity_pack_markdown_from_artifact(
                artifact_path,
                title=_optional_str(payload.get("title")),
            )
        else:
            request = ContinuityPackRequest(
                title=_required_str(payload, "title"),
                source_artifact_path=_required_str(payload, "source_artifact_path"),
                confirmed=_string_tuple(payload.get("confirmed"), field_name="confirmed"),
                assumptions=_string_tuple(payload.get("assumptions"), field_name="assumptions"),
                to_verify=_string_tuple(payload.get("to_verify"), field_name="to_verify"),
                recommended_next_test=_string_tuple(
                    payload.get("recommended_next_test"),
                    field_name="recommended_next_test",
                ),
                decision_snapshot=_string_tuple(
                    payload.get("decision_snapshot", ()),
                    field_name="decision_snapshot",
                ),
            )
            markdown = self.delivery.render_continuity_pack_markdown(request)
        if markdown is None:
            return _json_response(
                start_response,
                "501 Not Implemented",
                {
                    "error": "continuity_pack_not_available",
                    "status": "unsupported",
                },
            )
        return _text_response(
            start_response,
            "200 OK",
            "text/markdown; charset=utf-8",
            markdown,
        )

    def _render_continuity_pack_view(
        self,
        environ: WsgiEnviron,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        artifact_path = _required_query_param(environ, "artifact_path")
        title = _optional_query_param(environ, "title")
        try:
            html = render_continuity_pack_html(
                self.delivery,
                artifact_path=artifact_path,
                title=title,
            )
        except ValueError as exc:
            return _html_response(
                start_response,
                "400 Bad Request",
                _render_error_html(
                    title="Continuity pack unavailable",
                    message=str(exc),
                ),
            )
        return _html_response(start_response, "200 OK", html)

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
        document = self.delivery.get_document(document_id)
        if document is None:
            return _json_response(
                start_response,
                "404 Not Found",
                {"error": "document_not_found", "status": "missing"},
            )
        if not self.delivery.list_chunks_for_document(document_id):
            inline_content = document.inline_content or ""
            if inline_content.strip():
                self.delivery.prepare_document(
                    DocumentPreparationRequest(
                        case_id=document.case_id,
                        document_id=document.document_id,
                        chunking_method=None,
                    ),
                    inline_content,
                )
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
            credibility_assessment_response_payload(outcome.assessment),
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
            credibility_assessment_response_payload(assessment),
        )


    def _render_research_result_html(
        self,
        path: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        job_id = path.removeprefix('/api/research/result/').removesuffix('.html').strip('/')
        if not job_id:
            return _json_response(start_response, '404 Not Found', {'error': 'not_found'})
        outcome = self.delivery.get_research_result(job_id)
        if outcome is None or outcome.result is None:
            return _json_response(
                start_response,
                '404 Not Found',
                {'error': 'research_result_not_found', 'status': 'missing'},
            )
        return _text_response(
            start_response,
            '200 OK',
            'text/html; charset=utf-8',
            _research_result_to_html(outcome.result),
        )

    def _render_report(
        self,
        path: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        report_ref = path.removeprefix("/api/reports/").strip("/")
        if report_ref.endswith(".html"):
            case_id = report_ref.removesuffix(".html")
            outcome = self.delivery.assemble_case_report(case_id)
            if not outcome.entries and not outcome.request.review_decisions:
                return _json_response(
                    start_response,
                    "404 Not Found",
                    {"error": "report_not_found", "status": "missing"},
                )
            return _text_response(
                start_response,
                "200 OK",
                "text/html; charset=utf-8",
                render_report_html(outcome),
            )
        if report_ref.endswith(".md"):
            case_id = report_ref.removesuffix(".md")
            outcome = self.delivery.assemble_case_report(case_id)
            if not outcome.entries and not outcome.request.review_decisions:
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
        if report_ref:
            case_id = report_ref.removesuffix(".json")
            outcome = self.delivery.assemble_case_report(case_id)
            if not outcome.entries and not outcome.request.review_decisions:
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




def _research_settings_to_payload(settings: ResearchSettings) -> dict[str, object]:
    return {
        "max_rounds": settings.max_rounds,
        "max_time_seconds": settings.max_time_seconds,
        "search_provider": settings.search_provider,
        "endpoint_id": settings.endpoint_id,
        "model": settings.model,
        "extraction_timeout_seconds": settings.extraction_timeout_seconds,
        "extraction_concurrency": settings.extraction_concurrency,
        "category": settings.category,
    }


def _research_job_to_payload(job: ResearchJob) -> dict[str, object]:
    return {
        "job_id": job.job_id,
        "owner_id": job.owner_id,
        "query": job.query,
        "status": job.status.value,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "settings": _research_settings_to_payload(job.settings),
        "error": job.error,
    }


def _research_progress_to_payload(event: ResearchProgressEvent) -> dict[str, object]:
    return {
        "job_id": event.job_id,
        "status": event.status.value,
        "phase": event.phase.value,
        "round": event.round,
        "queries": event.queries,
        "query_preview": event.query_preview,
        "total_sources": event.total_sources,
        "new_sources": event.new_sources,
        "total_findings": event.total_findings,
        "url": event.url,
        "title": event.title,
        "message": event.message,
        "final": event.final,
    }


def _compiled_research_artifact_lint_to_payload(lint: CompiledResearchArtifactLint) -> dict[str, object]:
    return {
        "lint_id": lint.lint_id,
        "artifact_id": lint.artifact_id,
        "owner_id": lint.owner_id,
        "status": lint.status.value,
        "completeness_verdict": lint.completeness_verdict.value,
        "evidence_verdict": lint.evidence_verdict.value,
        "followup_verdict": lint.followup_verdict.value,
        "risk_flags": list(lint.risk_flags),
        "missing_sections": list(lint.missing_sections),
        "recommended_repairs": list(lint.recommended_repairs),
        "recommended_next_action": lint.recommended_next_action,
        "created_at": lint.created_at,
    }


def _compiled_research_artifact_to_payload(artifact: CompiledResearchArtifact) -> dict[str, object]:
    return {
        "artifact_id": artifact.artifact_id,
        "source_job_id": artifact.source_job_id,
        "owner_id": artifact.owner_id,
        "query": artifact.query,
        "query_class": artifact.query_class.value,
        "title": artifact.title,
        "summary": artifact.summary,
        "current_answer": artifact.current_answer,
        "key_claims": [
            {"text": claim.text, "evidence_refs": list(claim.evidence_refs)}
            for claim in artifact.key_claims
        ],
        "supporting_evidence": [
            {"url": ref.url, "title": ref.title, "summary": ref.summary}
            for ref in artifact.supporting_evidence
        ],
        "open_questions": list(artifact.open_questions),
        "next_checks": list(artifact.next_checks),
        "source_refs": [
            {"url": source.url, "title": source.title, "image": source.image}
            for source in artifact.source_refs
        ],
        "evaluation_snapshot": {
            "query_class": artifact.evaluation_snapshot.query_class.value,
            "source_quality_verdict": artifact.evaluation_snapshot.source_quality_verdict.value,
            "source_quality_reasons": list(artifact.evaluation_snapshot.source_quality_reasons),
            "relevance_verdict": artifact.evaluation_snapshot.relevance_verdict.value,
            "relevance_risks": list(artifact.evaluation_snapshot.relevance_risks),
            "truthfulness_verdict": artifact.evaluation_snapshot.truthfulness_verdict.value,
            "overclaim_risks": list(artifact.evaluation_snapshot.overclaim_risks),
            "missing_checks": list(artifact.evaluation_snapshot.missing_checks),
            "recommended_next_check": artifact.evaluation_snapshot.recommended_next_check,
            "should_revise_report": artifact.evaluation_snapshot.should_revise_report,
        } if artifact.evaluation_snapshot is not None else None,
        "created_at": artifact.created_at,
    }


def _research_result_to_payload(result: ResearchResultArtifact) -> dict[str, object]:
    return {
        "job_id": result.job_id,
        "owner_id": result.owner_id,
        "query": result.query,
        "status": result.status.value,
        "completion_mode": result.completion_mode.value,
        "result": result.result,
        "raw_report": result.raw_report,
        "category": result.category,
        "stats": {
            "duration_seconds": result.stats.duration_seconds,
            "rounds": result.stats.rounds,
            "queries": result.stats.queries,
            "urls": result.stats.urls,
            "model": result.stats.model,
            "search_providers": list(result.stats.search_providers),
        },
        "sources": [
            {"url": source.url, "title": source.title, "image": source.image}
            for source in result.sources
        ],
        "raw_findings": [
            {"url": finding.url, "title": finding.title, "summary": finding.summary}
            for finding in result.raw_findings
        ],
        "evaluation": {
            "query_class": result.evaluation.query_class.value,
            "source_quality_verdict": result.evaluation.source_quality_verdict.value,
            "source_quality_reasons": list(result.evaluation.source_quality_reasons),
            "relevance_verdict": result.evaluation.relevance_verdict.value,
            "relevance_risks": list(result.evaluation.relevance_risks),
            "truthfulness_verdict": result.evaluation.truthfulness_verdict.value,
            "overclaim_risks": list(result.evaluation.overclaim_risks),
            "missing_checks": list(result.evaluation.missing_checks),
            "recommended_next_check": result.evaluation.recommended_next_check,
            "should_revise_report": result.evaluation.should_revise_report,
        } if result.evaluation is not None else None,
        "created_at": result.created_at,
        "completed_at": result.completed_at,
    }


def _research_result_to_html(result: ResearchResultArtifact) -> str:
    def esc(value: object) -> str:
        return _escape_html(str(value if value is not None else ''))

    evaluation = result.evaluation
    evaluation_html = (
        "<p><strong>Query class:</strong> n/a</p>"
        "<p><strong>Source quality:</strong> n/a</p>"
        "<p><strong>Relevance:</strong> n/a</p>"
        "<p><strong>Truthfulness:</strong> n/a</p>"
        if evaluation is None
        else (
            f"<p><strong>Query class:</strong> {esc(evaluation.query_class.value)}</p>"
            f"<p><strong>Source quality:</strong> {esc(evaluation.source_quality_verdict.value)}</p>"
            f"<p><strong>Relevance:</strong> {esc(evaluation.relevance_verdict.value)}</p>"
            f"<p><strong>Truthfulness:</strong> {esc(evaluation.truthfulness_verdict.value)}</p>"
            f"<p><strong>Recommended next check:</strong> {esc(evaluation.recommended_next_check or 'none')}</p>"
            f"<p><strong>Should revise report:</strong> {esc('yes' if evaluation.should_revise_report else 'no')}</p>"
        )
    )
    findings = ''.join(
        f'<li><a href="{esc(f.url)}">{esc(f.title)}</a><br><small>{esc(f.summary)}</small></li>'
        for f in result.raw_findings[:10]
    ) or '<li>No findings captured.</li>'
    sources = ''.join(
        f'<li><a href="{esc(s.url)}">{esc(s.title)}</a></li>'
        for s in result.sources[:10]
    ) or '<li>No sources captured.</li>'
    return (
        "<!doctype html>"
        "<html><head><title>SourceTrace Deep Research Report</title></head>"
        "<body>"
        f"<h1>Deep Research Report</h1>"
        f"<p><strong>Job ID:</strong> {esc(result.job_id)}</p>"
        f"<p><strong>Query:</strong> {esc(result.query)}</p>"
        f"<p><strong>Status:</strong> {esc(result.status.value)}</p>"
        f"<p><strong>Completion mode:</strong> {esc(result.completion_mode.value)}</p>"
        f"<p><strong>Providers:</strong> {esc(', '.join(result.stats.search_providers) if result.stats.search_providers else 'none')}</p>"
        f"<h2>Current answer</h2><div>{esc(result.result).replace(chr(10), '<br>')}</div>"
        f"<h2>Evaluation</h2>{evaluation_html}"
        f"<h2>Findings</h2><ul>{findings}</ul>"
        f"<h2>Sources</h2><ul>{sources}</ul>"
        "</body></html>"
    )

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


def _required_str(payload: dict[str, object], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ValueError(f"{key} is required.")
    return value


def _string_tuple(value: object, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        raise ValueError(f"{field_name} must be an array of strings.")
    if not isinstance(value, list | tuple):
        raise ValueError(f"{field_name} must be an array of strings.")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{field_name} must be an array of strings.")
        stripped = item.strip()
        if stripped:
            items.append(stripped)
    return tuple(items)


def _required_query_param(environ: WsgiEnviron, name: str) -> str:
    with suppress(Exception):
        from urllib.parse import parse_qs

        query = parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=True)
        value = (query.get(name) or [""])[0].strip()
        if value:
            return value
    raise ValueError(f"{name} query parameter is required.")


def _optional_query_param(environ: WsgiEnviron, name: str) -> str | None:
    with suppress(Exception):
        from urllib.parse import parse_qs

        query = parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=True)
        value = (query.get(name) or [""])[0].strip()
        return value or None
    return None


def _render_error_html(*, title: str, message: str) -> str:
    safe_title = _escape_html(title)
    safe_message = _escape_html(message)
    return (
        "<!doctype html>"
        f"<html><head><title>{safe_title}</title></head>"
        "<body>"
        f"<h1>{safe_title}</h1>"
        f"<p>{safe_message}</p>"
        "</body></html>"
    )


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


def _sse_response(
    start_response: StartResponse,
    *,
    events: list[dict[str, object]],
    final_payload: dict[str, object],
) -> Iterable[bytes]:
    frames: list[bytes] = []
    for event in events:
        payload = json.dumps(event, sort_keys=True)
        frames.append(f"event: progress\ndata: {payload}\n\n".encode("utf-8"))
    payload = json.dumps(final_payload, sort_keys=True)
    frames.append(f"event: done\ndata: {payload}\n\n".encode("utf-8"))
    body = b"".join(frames)
    start_response(
        "200 OK",
        [
            ("Content-Type", "text/event-stream; charset=utf-8"),
            ("Cache-Control", "no-cache"),
            ("Connection", "keep-alive"),
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


def _redirect_response(
    start_response: StartResponse,
    location: str,
) -> Iterable[bytes]:
    body = b""
    start_response(
        "303 See Other",
        [
            ("Location", location),
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
        '<p><a href="/research">Open Research console</a></p>'
        "<h2>Research UI v1</h2>"
        "<p>Minimal read-path for Deep Research progress and result inspection.</p>"
        "<ul>"
        "<li><code>POST /api/research/start</code></li>"
        "<li><code>GET /api/research/jobs?owner_id=...</code></li>"
        "<li><code>GET /api/research/status/{job_id}</code></li>"
        "<li><code>GET /api/research/stream/{job_id}</code></li>"
        "<li><code>GET /api/research/result/{job_id}</code></li>"
        "<li><code>GET /api/research/result/{job_id}.html</code></li>"
        "<li><code>POST /api/research/run/{job_id}</code></li>"
        "<li><code>POST /api/research/cancel/{job_id}</code></li>"
        "</ul>"
        "<p>Suggested operator flow: start a job, run it, read status/stream/result, verify the same state is visible through the API and this UI route list.</p>"
        "<h2>Available routes</h2>"
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


def _render_research_console_html() -> str:
    return r"""<!doctype html>
<html>
  <head>
    <title>SourceTrace Research Console</title>
    <style>
      :root {
        color-scheme: dark;
        --bg: #08111f;
        --panel: rgba(10, 22, 41, 0.88);
        --panel-strong: rgba(12, 26, 49, 0.98);
        --panel-soft: rgba(15, 32, 58, 0.72);
        --text: #e8eefc;
        --muted: #94a8c9;
        --line: rgba(148, 168, 201, 0.18);
        --accent: #67b7ff;
        --accent-2: #8a7dff;
        --ok: #21c47b;
        --warn: #ffb648;
        --danger: #ff6b7a;
        --shadow: 0 22px 60px rgba(0, 0, 0, 0.35);
        --radius: 20px;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        min-height: 100vh;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background:
          radial-gradient(circle at top left, rgba(103, 183, 255, 0.16), transparent 32%),
          radial-gradient(circle at top right, rgba(138, 125, 255, 0.18), transparent 28%),
          linear-gradient(180deg, #0a1221 0%, #08111f 58%, #060d18 100%);
        color: var(--text);
      }
      a { color: var(--accent); }
      .shell {
        width: min(1440px, calc(100vw - 32px));
        margin: 28px auto;
        display: grid;
        gap: 20px;
      }
      .hero {
        display: grid;
        grid-template-columns: 1.5fr 0.9fr;
        gap: 20px;
      }
      .card {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: var(--radius);
        box-shadow: var(--shadow);
        backdrop-filter: blur(18px);
      }
      .hero-main {
        padding: 28px;
      }
      .hero-side {
        padding: 24px;
        display: grid;
        gap: 14px;
        align-content: start;
      }
      .eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border-radius: 999px;
        background: rgba(103, 183, 255, 0.12);
        border: 1px solid rgba(103, 183, 255, 0.18);
        color: #cfe5ff;
        font-size: 13px;
        letter-spacing: 0.02em;
      }
      h1, h2, h3 { margin: 0; }
      h1 {
        font-size: clamp(30px, 4vw, 48px);
        line-height: 1.05;
        margin-top: 18px;
        letter-spacing: -0.03em;
      }
      .lede {
        margin-top: 14px;
        max-width: 760px;
        color: var(--muted);
        font-size: 16px;
        line-height: 1.6;
      }
      .summary-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-top: 22px;
      }
      .metric {
        padding: 16px;
        border-radius: 16px;
        background: var(--panel-soft);
        border: 1px solid var(--line);
      }
      .metric-label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }
      .metric-value { font-size: 24px; font-weight: 700; margin-top: 6px; }
      .metric-sub { color: var(--muted); font-size: 13px; margin-top: 4px; }
      .stack { display: grid; gap: 20px; }
      .controls { padding: 24px; }
      .section-title {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        margin-bottom: 16px;
      }
      .muted { color: var(--muted); }
      .field-grid {
        display: grid;
        grid-template-columns: 0.85fr 1.15fr;
        gap: 16px;
      }
      label {
        display: block;
        margin-bottom: 8px;
        color: #d8e3fb;
        font-weight: 600;
        font-size: 14px;
      }
      input, textarea, button {
        font: inherit;
      }
      input, textarea {
        width: 100%;
        border-radius: 14px;
        border: 1px solid rgba(148, 168, 201, 0.16);
        background: rgba(5, 13, 24, 0.58);
        color: var(--text);
        padding: 14px 15px;
        outline: none;
        transition: border-color 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease;
      }
      textarea { min-height: 144px; resize: vertical; }
      input:focus, textarea:focus {
        border-color: rgba(103, 183, 255, 0.55);
        box-shadow: 0 0 0 4px rgba(103, 183, 255, 0.12);
      }
      .action-row {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 18px;
      }
      button {
        border: 0;
        border-radius: 12px;
        padding: 12px 16px;
        cursor: pointer;
        color: #08111f;
        background: linear-gradient(135deg, #8ed0ff 0%, #67b7ff 100%);
        font-weight: 700;
        letter-spacing: 0.01em;
        transition: transform 0.16s ease, box-shadow 0.16s ease, opacity 0.16s ease;
        box-shadow: 0 12px 30px rgba(103, 183, 255, 0.25);
      }
      button:hover { transform: translateY(-1px); }
      button.secondary {
        background: rgba(148, 168, 201, 0.12);
        color: var(--text);
        box-shadow: none;
        border: 1px solid rgba(148, 168, 201, 0.14);
      }
      .workspace {
        display: grid;
        grid-template-columns: 1.35fr 0.95fr;
        gap: 20px;
      }
      .result-shell {
        display: grid;
        gap: 18px;
        padding: 24px;
      }
      .status-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
      }
      .surface {
        background: var(--panel-strong);
        border: 1px solid var(--line);
        border-radius: 18px;
        overflow: hidden;
      }
      .surface-head {
        padding: 14px 16px;
        border-bottom: 1px solid var(--line);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
      }
      .surface-head h3 { font-size: 15px; }
      .surface-body {
        padding: 16px;
      }
      .mono {
        font-family: "SFMono-Regular", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        white-space: pre-wrap;
        word-break: break-word;
        line-height: 1.5;
        font-size: 13px;
      }
      .console {
        min-height: 220px;
        max-height: 420px;
        overflow: auto;
        background: rgba(3, 10, 20, 0.58);
        border-radius: 14px;
        padding: 14px;
      }
      .report {
        min-height: 280px;
        max-height: 760px;
        overflow: auto;
        background: linear-gradient(180deg, rgba(4, 10, 19, 0.92), rgba(7, 16, 30, 0.8));
        border-radius: 18px;
        border: 1px solid rgba(148, 168, 201, 0.12);
        padding: 20px;
        line-height: 1.7;
      }
      .report h2 { margin-top: 0; font-size: 20px; }
      .report h3 { margin: 18px 0 10px; font-size: 16px; }
      .report p, .report li { color: #d9e4fa; }
      .report ul { padding-left: 20px; }
      .pill-row {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }
      .pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border-radius: 999px;
        border: 1px solid var(--line);
        background: rgba(148, 168, 201, 0.08);
        font-size: 13px;
      }
      .badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 88px;
        padding: 8px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }
      .badge.ok { color: #082516; background: rgba(33, 196, 123, 0.92); }
      .badge.warn { color: #2d1800; background: rgba(255, 182, 72, 0.92); }
      .badge.danger { color: #390a12; background: rgba(255, 107, 122, 0.95); }
      .eval-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
      }
      .eval-card {
        padding: 14px;
        border-radius: 16px;
        background: rgba(148, 168, 201, 0.08);
        border: 1px solid var(--line);
      }
      .eval-card h4 { margin: 0 0 10px; font-size: 13px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; }
      .eval-card .verdict { font-size: 18px; font-weight: 800; margin-bottom: 8px; }
      .list-card {
        padding: 18px;
        display: grid;
        gap: 12px;
      }
      .job-list {
        display: grid;
        gap: 10px;
        max-height: 420px;
        overflow: auto;
      }
      .job-item {
        padding: 14px;
        border-radius: 14px;
        border: 1px solid var(--line);
        background: rgba(148, 168, 201, 0.06);
        cursor: pointer;
        transition: transform 0.16s ease, border-color 0.16s ease, background 0.16s ease;
      }
      .job-item:hover { transform: translateY(-1px); border-color: rgba(103, 183, 255, 0.35); }
      .job-item strong { display: block; margin-bottom: 6px; }
      .job-meta { font-size: 12px; color: var(--muted); }
      .split {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
      }
      .helper {
        padding: 14px;
        border-radius: 16px;
        background: rgba(103, 183, 255, 0.08);
        border: 1px solid rgba(103, 183, 255, 0.18);
        color: #dcecff;
      }
      .hidden { display: none !important; }
      @media (max-width: 1180px) {
        .hero, .workspace, .field-grid, .status-grid, .eval-grid, .split { grid-template-columns: 1fr; }
        .summary-grid { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <div class="shell">
      <section class="hero">
        <div class="card hero-main">
          <div class="eyebrow">Deep Research · operator console</div>
          <h1>Research UI — modern operator view</h1>
          <p class="lede">Run jobs, inspect evidence flow, read the result, and now review the post-result evaluator without falling back to raw JSON unless you want to.</p>
          <div class="summary-grid">
            <div class="metric">
              <div class="metric-label">Mode</div>
              <div class="metric-value">Live API</div>
              <div class="metric-sub">Start, run, status, stream, result</div>
            </div>
            <div class="metric">
              <div class="metric-label">Evaluator</div>
              <div class="metric-value">v1</div>
              <div class="metric-sub">Structured quality diagnostics</div>
            </div>
            <div class="metric">
              <div class="metric-label">Flow</div>
              <div class="metric-value">Operator-first</div>
              <div class="metric-sub">Readable by default, raw on demand</div>
            </div>
          </div>
        </div>
        <aside class="card hero-side">
          <div>
            <div class="metric-label">What changed</div>
            <div class="metric-value" style="font-size: 20px;">Evaluation-aware results</div>
            <div class="metric-sub">Source quality, relevance, truthfulness, risks, next check.</div>
          </div>
          <div class="helper">
            Tip: use one owner id per benchmark slice so you can compare runs without losing the job history.
          </div>
          <div class="pill-row">
            <span class="pill">/research</span>
            <span class="pill">Readable status</span>
            <span class="pill">Evaluator summary</span>
          </div>
        </aside>
      </section>

      <section class="card controls">
        <div class="section-title">
          <div>
            <h2>Run a research job</h2>
            <div class="muted">Start from a query, then inspect stream, result, and evaluator output in one place.</div>
          </div>
          <div class="pill-row">
            <span id="connection_pill" class="pill">idle</span>
            <span id="job_state_pill" class="pill">no job selected</span>
          </div>
        </div>
        <div class="field-grid">
          <div>
            <label for="owner_id">Owner id</label>
            <input id="owner_id" value="user-1" />
          </div>
          <div>
            <label for="job_id">Job id</label>
            <input id="job_id" placeholder="job id appears here after start" />
          </div>
        </div>
        <div style="margin-top: 16px;">
          <label for="query">Query</label>
          <textarea id="query">deep research architecture</textarea>
        </div>
        <div class="action-row">
          <button id="start_btn">Start job</button>
          <button id="run_btn">Run job</button>
          <button id="refresh_btn" class="secondary">Refresh status</button>
          <button id="result_btn" class="secondary">Load result</button>
          <button id="jobs_btn" class="secondary">List jobs</button>
        </div>
      </section>

      <section class="workspace">
        <div class="stack">
          <div class="status-grid">
            <div class="surface">
              <div class="surface-head">
                <h3>Status snapshot</h3>
                <span class="muted">Readable + raw</span>
              </div>
              <div class="surface-body">
                <div id="status_summary" class="helper">No job yet.</div>
                <div id="status_box" class="console mono" style="margin-top: 12px;">No job yet.</div>
              </div>
            </div>
            <div class="surface">
              <div class="surface-head">
                <h3>Progress stream</h3>
                <span class="muted">Polling fallback</span>
              </div>
              <div class="surface-body">
                <div id="stream_box" class="console mono">No stream yet.</div>
              </div>
            </div>
          </div>

          <div class="card result-shell">
            <div class="section-title">
              <div>
                <h2>Result + evaluator</h2>
                <div class="muted">Readable report first. Diagnostics beside it. Raw JSON only when needed.</div>
              </div>
              <div class="pill-row">
                <span id="result_banner" class="pill">No result yet</span>
                <span id="query_class_pill" class="pill">query class: n/a</span>
              </div>
            </div>
            <div class="split">
              <div class="surface">
                <div class="surface-head">
                  <h3>Final report</h3>
                  <div class="pill-row">
                    <button id="html_btn" class="secondary">HTML</button>
                    <button id="preview_btn" class="secondary">Markdown</button>
                    <button id="raw_btn" class="secondary">JSON</button>
                  </div>
                </div>
                <div class="surface-body">
                  <iframe id="result_html" class="report hidden" title="HTML report preview"></iframe>
                  <div id="result_preview" class="report">No result yet.</div>
                  <div id="result_box" class="console mono hidden">No result yet.</div>
                </div>
              </div>
              <div class="surface">
                <div class="surface-head">
                  <h3>Evaluator output</h3>
                  <span class="muted">Diagnostic first</span>
                </div>
                <div class="surface-body stack">
                  <div class="eval-grid">
                    <div class="eval-card">
                      <h4>Source quality</h4>
                      <div id="eval_source_verdict" class="verdict">n/a</div>
                      <div id="eval_source_reasons" class="muted">No evaluation yet.</div>
                    </div>
                    <div class="eval-card">
                      <h4>Relevance</h4>
                      <div id="eval_relevance_verdict" class="verdict">n/a</div>
                      <div id="eval_relevance_risks" class="muted">No evaluation yet.</div>
                    </div>
                    <div class="eval-card">
                      <h4>Truthfulness</h4>
                      <div id="eval_truth_verdict" class="verdict">n/a</div>
                      <div id="eval_truth_risks" class="muted">No evaluation yet.</div>
                    </div>
                  </div>
                  <div class="split">
                    <div class="eval-card">
                      <h4>Missing checks</h4>
                      <div id="eval_missing_checks" class="muted">No evaluation yet.</div>
                    </div>
                    <div class="eval-card">
                      <h4>Recommended next check</h4>
                      <div id="eval_next_check">No evaluation yet.</div>
                      <div id="eval_revise" class="muted" style="margin-top: 10px;">should_revise_report: n/a</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <aside class="card list-card">
          <div class="section-title">
            <div>
              <h2>Jobs</h2>
              <div class="muted">Click a job to load status and result.</div>
            </div>
          </div>
          <div id="jobs_box" class="console mono">No jobs loaded.</div>
          <div id="jobs_list" class="job-list"></div>
          <div class="helper">The list is owner-scoped. Reuse the same owner id when running benchmark comparisons.</div>
          <p class="muted"><a href="/">Back to home</a></p>
        </aside>
      </section>
    </div>

    <script>
      const ownerInput = document.getElementById('owner_id');
      const queryInput = document.getElementById('query');
      const jobInput = document.getElementById('job_id');
      const statusSummary = document.getElementById('status_summary');
      const statusBox = document.getElementById('status_box');
      const streamBox = document.getElementById('stream_box');
      const resultBox = document.getElementById('result_box');
      const resultPreview = document.getElementById('result_preview');
      const resultHtml = document.getElementById('result_html');
      const resultBanner = document.getElementById('result_banner');
      const queryClassPill = document.getElementById('query_class_pill');
      const jobsBox = document.getElementById('jobs_box');
      const jobsList = document.getElementById('jobs_list');
      const connectionPill = document.getElementById('connection_pill');
      const jobStatePill = document.getElementById('job_state_pill');
      const evalSourceVerdict = document.getElementById('eval_source_verdict');
      const evalSourceReasons = document.getElementById('eval_source_reasons');
      const evalRelevanceVerdict = document.getElementById('eval_relevance_verdict');
      const evalRelevanceRisks = document.getElementById('eval_relevance_risks');
      const evalTruthVerdict = document.getElementById('eval_truth_verdict');
      const evalTruthRisks = document.getElementById('eval_truth_risks');
      const evalMissingChecks = document.getElementById('eval_missing_checks');
      const evalNextCheck = document.getElementById('eval_next_check');
      const evalRevise = document.getElementById('eval_revise');
      let refreshTimer = null;

      function setText(el, value) {
        el.textContent = value;
      }

      function setBox(el, value, cls='console mono') {
        el.className = cls;
        el.textContent = value;
      }

      function verdictTone(value) {
        if (value === 'strong') return 'ok';
        if (value === 'weak') return 'danger';
        return 'warn';
      }

      function renderVerdict(el, value) {
        el.textContent = value ? value.toUpperCase() : 'N/A';
        el.style.color = value === 'strong' ? 'var(--ok)' : value === 'weak' ? 'var(--danger)' : 'var(--warn)';
      }

      function renderLines(lines, fallback='None') {
        if (!Array.isArray(lines) || !lines.length) return fallback;
        return lines.map((line) => `• ${line}`).join(String.fromCharCode(10));
      }

      function renderStreamText(payload) {
        const progress = Array.isArray(payload.progress) ? payload.progress : [];
        if (!progress.length) return 'No progress events yet.';
        return progress.map((event) => {
          const bits = [event.phase, event.status];
          if (event.round) bits.push(`round=${event.round}`);
          if (event.total_sources) bits.push(`sources=${event.total_sources}`);
          if (event.total_findings) bits.push(`findings=${event.total_findings}`);
          if (event.message) bits.push(`msg=${event.message}`);
          return bits.join(' | ');
        }).join(String.fromCharCode(10));
      }

      function markdownToHtml(markdown) {
        const escaped = String(markdown || '')
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;');
        return escaped
          .replace(/^### (.*)$/gm, '<h3>$1</h3>')
          .replace(/^## (.*)$/gm, '<h2>$1</h2>')
          .replace(/^# (.*)$/gm, '<h1>$1</h1>')
          .replace(/[*][*](.*?)[*][*]/g, '<strong>$1</strong>')
          .replace(/^- (.*)$/gm, '<li>$1</li>')
          .replace(/(<li>.*[<]\/li>)/gs, '<ul>$1</ul>')
          .replace(/\n\n/g, '</p><p>')
          .replace(/^/, '<p>')
          .replace(/$/, '</p>')
          .replace(/<p><\/p>/g, '')
          .replace(/<p>(<h[1-3]>)/g, '$1')
          .replace(/(<\/h[1-3]>)<\/p>/g, '$1')
          .replace(/<p>(<ul>)/g, '$1')
          .replace(/(<\/ul>)<\/p>/g, '$1');
      }

      function renderStatusSummary(payload) {
        const job = payload.job || {};
        const lines = [
          `job_id: ${job.job_id || 'n/a'}`,
          `status: ${job.status || 'n/a'}`,
          `query: ${job.query || 'n/a'}`,
        ];
        if (job.completed_at) lines.push(`completed_at: ${job.completed_at}`);
        statusSummary.textContent = lines.join(String.fromCharCode(10));
        jobStatePill.textContent = job.status ? `job: ${job.status}` : 'no job selected';
      }

      function renderJobsList(payload) {
        const jobs = Array.isArray(payload.jobs) ? payload.jobs : [];
        jobsList.innerHTML = '';
        for (const job of jobs) {
          const item = document.createElement('button');
          item.type = 'button';
          item.className = 'job-item';
          item.innerHTML = `<strong>${job.job_id}</strong><div>${job.query || 'no query'}</div><div class="job-meta">${job.status} · ${job.created_at || 'n/a'}</div>`;
          item.onclick = async () => {
            jobInput.value = job.job_id;
            await refreshStatus();
            await loadResult();
          };
          jobsList.appendChild(item);
        }
      }

      async function jsonRequest(url, options={}) {
        connectionPill.textContent = 'loading';
        const response = await fetch(url, options);
        const text = await response.text();
        let payload;
        try { payload = JSON.parse(text); } catch { payload = { raw: text }; }
        if (!response.ok) {
          connectionPill.textContent = 'error';
          const message = payload && (payload.error || payload.status || payload.raw)
            ? String(payload.error || payload.status || payload.raw)
            : `HTTP ${response.status}`;
          throw new Error(`${response.status} ${response.statusText}: ${message}`);
        }
        connectionPill.textContent = 'ok';
        return { response, payload };
      }

      function showUiError(prefix, error) {
        const message = error instanceof Error ? error.message : String(error);
        setBox(statusSummary, `${prefix}: ${message}`, 'helper');
        setBox(statusBox, `${prefix}: ${message}`, 'console mono');
        connectionPill.textContent = 'error';
      }

      function renderEvaluation(evaluation) {
        if (!evaluation) {
          queryClassPill.textContent = 'query class: n/a';
          renderVerdict(evalSourceVerdict, '');
          renderVerdict(evalRelevanceVerdict, '');
          renderVerdict(evalTruthVerdict, '');
          setText(evalSourceReasons, 'No evaluation yet.');
          setText(evalRelevanceRisks, 'No evaluation yet.');
          setText(evalTruthRisks, 'No evaluation yet.');
          setText(evalMissingChecks, 'No evaluation yet.');
          setText(evalNextCheck, 'No evaluation yet.');
          setText(evalRevise, 'should_revise_report: n/a');
          return;
        }
        queryClassPill.textContent = `query class: ${evaluation.query_class}`;
        renderVerdict(evalSourceVerdict, evaluation.source_quality_verdict);
        renderVerdict(evalRelevanceVerdict, evaluation.relevance_verdict);
        renderVerdict(evalTruthVerdict, evaluation.truthfulness_verdict);
        setText(evalSourceReasons, renderLines(evaluation.source_quality_reasons, 'No specific source-quality notes.'));
        setText(evalRelevanceRisks, renderLines(evaluation.relevance_risks, 'No specific relevance risks.'));
        setText(evalTruthRisks, renderLines(evaluation.overclaim_risks, 'No explicit overclaim risks flagged.'));
        setText(evalMissingChecks, renderLines(evaluation.missing_checks, 'No missing checks flagged.'));
        setText(evalNextCheck, evaluation.recommended_next_check || 'No recommended next check.');
        setText(evalRevise, `should_revise_report: ${evaluation.should_revise_report ? 'yes' : 'no'}`);
      }

      async function startJob() {
        try {
          const ownerId = ownerInput.value.trim().toLowerCase();
          const query = queryInput.value.trim();
          if (!ownerId) {
            showUiError('Start failed', 'owner_id is required');
            return;
          }
          if (!query) {
            showUiError('Start failed', 'query is required');
            return;
          }
          ownerInput.value = ownerId;
          const { payload } = await jsonRequest('/api/research/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ owner_id: ownerId, query }),
          });
          if (payload.job && payload.job.job_id) {
            jobInput.value = payload.job.job_id;
            setBox(statusSummary, `Job created: ${payload.job.job_id}`, 'helper');
            await refreshStatus();
            await listJobs();
            startAutoRefresh();
            return;
          }
          showUiError('Start failed', 'server did not return a job id');
        } catch (error) {
          showUiError('Start failed', error);
        }
      }

      async function runJob() {
        const jobId = jobInput.value.trim();
        if (!jobId) {
          showUiError('Run failed', 'job_id is required');
          return;
        }
        setBox(statusSummary, `Running job: ${jobId}`, 'helper');
        setBox(statusBox, `POST /api/research/run/${jobId}`, 'console mono');
        try {
          const { payload } = await jsonRequest(`/api/research/run/${jobId}`, { method: 'POST' });
          const status = payload && payload.job && payload.job.status ? payload.job.status : 'unknown';
          const errorText = payload && payload.job && payload.job.error ? `\nerror: ${payload.job.error}` : '';
          setBox(statusSummary, `Run completed: ${jobId} (${status})`, 'helper');
          setBox(statusBox, `${JSON.stringify(payload, null, 2)}${errorText}`, 'console mono');
          await refreshStatus();
          await readStream();
          await loadResult();
          await listJobs();
          startAutoRefresh();
        } catch (error) {
          const message = error instanceof Error ? error.message : String(error);
          setBox(statusSummary, `Run failed: ${jobId}`, 'helper');
          setBox(statusBox, `POST /api/research/run/${jobId}\n${message}`, 'console mono');
          connectionPill.textContent = 'error';
          await refreshStatus();
        }
      }

      async function refreshStatus() {
        const jobId = jobInput.value.trim();
        if (!jobId) return;
        const { payload } = await jsonRequest(`/api/research/status/${jobId}`);
        renderStatusSummary(payload);
        setBox(statusBox, JSON.stringify(payload, null, 2), 'console mono');
        setBox(streamBox, renderStreamText(payload), 'console mono');
        const status = payload.job && payload.job.status ? payload.job.status : '';
        if (['done', 'error', 'cancelled'].includes(status)) {
          stopAutoRefresh();
        }
      }

      async function loadResult() {
        const jobId = jobInput.value.trim();
        if (!jobId) return;
        const { payload } = await jsonRequest(`/api/research/result/${jobId}`);
        const completion = payload.result && payload.result.completion_mode ? payload.result.completion_mode : 'pending';
        resultBanner.textContent = `completion_mode: ${completion}`;
        resultBanner.className = `badge ${completion === 'partial_error' ? 'warn' : completion === 'fallback' ? 'warn' : 'ok'}`;
        const markdown = payload.result && payload.result.result ? payload.result.result : 'No result yet.';
        resultPreview.innerHTML = markdownToHtml(markdown);
        resultHtml.src = `/api/research/result/${jobId}.html`;
        setBox(resultBox, JSON.stringify(payload, null, 2), 'console mono');
        renderEvaluation(payload.result ? payload.result.evaluation : null);
      }

      async function listJobs() {
        const ownerId = ownerInput.value.trim().toLowerCase();
        if (!ownerId) return;
        ownerInput.value = ownerId;
        const { payload } = await jsonRequest(`/api/research/jobs?owner_id=${encodeURIComponent(ownerId)}`);
        setBox(jobsBox, JSON.stringify(payload, null, 2), 'console mono');
        renderJobsList(payload);
      }

      async function readStream() {
        const jobId = jobInput.value.trim();
        if (!jobId) return;
        try {
          const response = await fetch(`/api/research/stream/${jobId}`);
          const text = await response.text();
          setBox(streamBox, text, 'console mono');
        } catch {
          await refreshStatus();
        }
      }

      function startAutoRefresh() {
        stopAutoRefresh();
        refreshTimer = window.setInterval(async () => {
          await refreshStatus();
        }, 1500);
      }

      function stopAutoRefresh() {
        if (refreshTimer !== null) {
          window.clearInterval(refreshTimer);
          refreshTimer = null;
        }
      }

      document.getElementById('start_btn').addEventListener('click', startJob);
      document.getElementById('run_btn').addEventListener('click', runJob);
      document.getElementById('refresh_btn').addEventListener('click', refreshStatus);
      document.getElementById('result_btn').addEventListener('click', loadResult);
      document.getElementById('jobs_btn').addEventListener('click', listJobs);
      document.getElementById('html_btn').addEventListener('click', () => {
        resultHtml.classList.remove('hidden');
        resultPreview.classList.add('hidden');
        resultBox.classList.add('hidden');
      });
      document.getElementById('preview_btn').addEventListener('click', () => {
        resultHtml.classList.add('hidden');
        resultPreview.classList.remove('hidden');
        resultBox.classList.add('hidden');
      });
      document.getElementById('raw_btn').addEventListener('click', () => {
        resultHtml.classList.add('hidden');
        resultPreview.classList.add('hidden');
        resultBox.classList.remove('hidden');
      });
    </script>
  </body>
</html>
"""


__all__ = [
    "SourceTraceServerRuntime",
    "SourceTraceWSGIApp",
    "create_wsgi_app",
    "create_wsgi_server",
    "run_local_server",
]
