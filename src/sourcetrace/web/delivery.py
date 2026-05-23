"""Thin analyst-facing delivery service over the runtime path."""

import os

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from unicodedata import combining, normalize as unicode_normalize
from hashlib import sha256
from typing import TYPE_CHECKING
from urllib.parse import quote as url_quote
from uuid import uuid4

from sourcetrace.application import (
    CONTINUITY_PACK_SECTIONS,
    CaseCreationOutcome,
    CaseCreationRequest,
    ClaimExtractionOutcome,
    ClaimExtractionRequest,
    ClaimExtractionRuntime,
    ContinuityPack,
    ContinuityPackOutcome,
    ContinuityPackRequest,
    CredibilityAssessmentExecution,
    CredibilityAssessmentOutcome,
    CredibilityAssessmentRequest,
    DocumentPreparationOutcome,
    DocumentPreparationRequest,
    ReportAssemblyExecution,
    ReportAssemblyOutcome,
    ReportAssemblyRequest,
    SourceIngestionOutcome,
    SourceIngestionRequest,
    build_continuity_pack_request_from_artifact,
    build_llm_credibility_assessor,
    render_continuity_pack_markdown,
)
from sourcetrace.application.interfaces import (
    ClaimVerificationExecution,
    ContinuityPackExecution,
)
from sourcetrace.application.extraction_runtime import build_llm_claim_extractor
from sourcetrace.domain import (
    Case,
    CaseReport,
    Claim,
    ClaimEvidenceLink,
    ClaimReportEntry,
    ClaimReviewDecision,
    ClaimVerification,
    Document,
    DocumentChunk,
    DocumentCredibilityAssessment,
)
from sourcetrace.domain.types import (
    AnalystDisposition,
    HumanReviewStatus,
    VerificationVerdict,
)
from sourcetrace.pipeline import (
    ClaimVerificationRuntime,
    ClaimVerificationRuntimeOutcome,
    ClaimVerificationRuntimeRequest,
    EvidencePresenceClaimVerifier,
    LexicalChunkRetriever,
    RetrievalExecution,
)
from sourcetrace.storage import (
    ContinuityPackPersistenceStatus,
    FileBackedCaseRepository,
    create_in_memory_persistence,
)
from sourcetrace.storage.interfaces import CorePersistence

if TYPE_CHECKING:
    from sourcetrace.llm.interfaces import (
        ClaimExtractionGateway,
        ClaimNormalizationGateway,
        CredibilityDraftGateway,
    )


@dataclass(frozen=True)
class VerificationDeliveryRequest:
    """Delivery-layer request for running the claim verification path."""

    claim: Claim
    requested_k: int = 3
    query_id: str | None = None
    retrieval_method: str | None = None
    document_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class VerificationInspection:
    """Analyst-facing view of a persisted verification result."""

    claim: Claim
    verification: ClaimVerification
    evidence_links: tuple[ClaimEvidenceLink, ...]
    evidence_count: int
    supporting_evidence_count: int
    contradicting_evidence_count: int
    insufficient_evidence_count: int
    has_review: bool
    has_report_entry: bool


@dataclass(frozen=True)
class ContinuityPackInspection:
    """Analyst-facing view of an assembled continuity pack."""

    title: str
    source_artifact_path: str
    sections: dict[str, tuple[str, ...]]
    decision_snapshot: tuple[str, ...]


@dataclass(frozen=True)
class SourceTraceDelivery:
    """Delivery surface for product resources, verification, review, and reports."""

    persistence: CorePersistence
    verification_runtime: ClaimVerificationRuntime
    report_assembly: ReportAssemblyExecution
    continuity_pack_execution: ContinuityPackExecution | None = None
    credibility_assessment: CredibilityAssessmentExecution | None = None
    claim_extraction_runtime: ClaimExtractionRuntime | None = None

    def create_case(
        self,
        request: CaseCreationRequest,
    ) -> CaseCreationOutcome:
        """Create and persist a case resource."""

        case = Case(
            case_id=request.case_id,
            title=request.title,
            description=request.description,
        )
        case = self.persistence.cases.save_case(case)
        return CaseCreationOutcome(request=request, case=case)

    def list_cases(self) -> tuple[Case, ...]:
        """List persisted case resources."""

        return self.persistence.cases.list_cases()

    def get_case(self, case_id: str) -> Case | None:
        """Return one persisted case resource."""

        return self.persistence.cases.get_case(case_id)

    def ingest_document(
        self,
        request: SourceIngestionRequest,
        document: Document,
    ) -> SourceIngestionOutcome | None:
        """Attach a document resource to an existing case."""

        case = self.persistence.cases.get_case(request.case_id)
        if case is None:
            return None
        document = self.persistence.documents.save_document(document)
        self._remember_case_document(case, document.document_id)
        return SourceIngestionOutcome(request=request, document=document)

    def list_documents_for_case(self, case_id: str) -> tuple[Document, ...] | None:
        """List persisted documents for an existing case."""

        if self.persistence.cases.get_case(case_id) is None:
            return None
        return self.persistence.documents.list_documents_for_case(case_id)

    def get_document(self, document_id: str) -> Document | None:
        """Return one persisted document resource."""

        return self.persistence.documents.get_document(document_id)

    def prepare_document(
        self,
        request: DocumentPreparationRequest,
        raw_text: str,
    ) -> DocumentPreparationOutcome | None:
        """Prepare caller-provided document text into persisted chunks."""

        document = self.persistence.documents.get_document(request.document_id)
        if document is None or document.case_id != request.case_id:
            return None
        chunks = self.persistence.documents.save_chunks(
            _chunks_from_text(
                case_id=request.case_id,
                document_id=request.document_id,
                raw_text=raw_text,
            )
        )
        return DocumentPreparationOutcome(
            request=request,
            document=document,
            chunks=chunks,
        )

    def list_chunks_for_document(
        self,
        document_id: str,
    ) -> tuple[DocumentChunk, ...] | None:
        """List prepared chunks for one document."""

        document = self.persistence.documents.get_document(document_id)
        if document is None:
            return None
        return self.persistence.documents.list_chunks_for_document(
            document.case_id,
            document.document_id,
        )

    def extract_claims(
        self,
        document_id: str,
        *,
        extraction_method: str | None = None,
    ) -> ClaimExtractionOutcome | None:
        """Run configured claim extraction over a prepared document."""

        if self.claim_extraction_runtime is None:
            return None
        document = self.persistence.documents.get_document(document_id)
        if document is None:
            return None
        chunks = self.persistence.documents.list_chunks_for_document(
            document.case_id,
            document.document_id,
        )
        request = ClaimExtractionRequest(
            case_id=document.case_id,
            document_id=document.document_id,
            chunk_ids=tuple(chunk.chunk_id for chunk in chunks),
            extraction_method=extraction_method,
        )
        outcome = self.claim_extraction_runtime.extract_claims(
            request,
            document=document,
            chunks=chunks,
        )
        claims = self.persistence.claims.save_claims(outcome.claims)
        evidence_links = self.persistence.claims.save_evidence_links(
            outcome.evidence_links
        )
        self._remember_case_claims(
            document.case_id,
            tuple(claim.claim_id for claim in claims),
        )
        return ClaimExtractionOutcome(
            request=outcome.request,
            document=outcome.document,
            chunks=outcome.chunks,
            claims=claims,
            evidence_links=evidence_links,
            dropped_claim_items=outcome.dropped_claim_items,
            dropped_evidence_items=outcome.dropped_evidence_items,
            review_cautions=outcome.review_cautions,
        )

    def list_claims_for_case(self, case_id: str) -> tuple[Claim, ...] | None:
        """List persisted claims for an existing case."""

        if self.persistence.cases.get_case(case_id) is None:
            return None
        return self.persistence.claims.list_claims_for_case(case_id)

    def get_claim(self, claim_id: str) -> Claim | None:
        """Return one persisted claim resource."""

        return self.persistence.claims.get_claim(claim_id)

    def get_claim_verification(self, claim_id: str) -> ClaimVerification | None:
        """Return a persisted verification artifact for a claim."""

        return self.persistence.claims.get_verification(claim_id)

    def get_claim_review(self, claim_id: str) -> ClaimReviewDecision | None:
        """Return a persisted review artifact for a claim."""

        return self.persistence.claims.get_review_decision(claim_id)

    def list_claim_evidence(
        self,
        claim_id: str,
    ) -> tuple[ClaimEvidenceLink, ...] | None:
        """List persisted evidence links for a claim."""

        if self.persistence.claims.get_claim(claim_id) is None:
            return None
        return self.persistence.claims.list_evidence_links_for_claim(claim_id)

    def verify_claim(
        self,
        request: VerificationDeliveryRequest,
    ) -> ClaimVerificationRuntimeOutcome:
        """Run retrieval-backed verification and persist the resulting records."""

        outcome = self.verification_runtime(
            ClaimVerificationRuntimeRequest(
                claim=request.claim,
                requested_k=request.requested_k,
                query_id=request.query_id,
                retrieval_method=request.retrieval_method,
                document_ids=request.document_ids,
            )
        )
        self._remember_case_claims(request.claim.case_id, (request.claim.claim_id,))
        return outcome

    def inspect_verification(self, claim_id: str) -> VerificationInspection | None:
        """Return the persisted analyst inspection view for one verified claim."""

        claim = self.persistence.claims.get_claim(claim_id)
        verification = self.persistence.claims.get_verification(claim_id)
        if claim is None or verification is None:
            return None
        evidence_links = self.persistence.claims.list_evidence_links_for_claim(claim_id)
        review_decision = self.persistence.claims.get_review_decision(claim_id)
        return VerificationInspection(
            claim=claim,
            verification=verification,
            evidence_links=evidence_links,
            evidence_count=len(evidence_links),
            supporting_evidence_count=_count_evidence_links(
                evidence_links,
                VerificationVerdict.SUPPORT,
            ),
            contradicting_evidence_count=_count_evidence_links(
                evidence_links,
                VerificationVerdict.CONTRADICT,
            ),
            insufficient_evidence_count=_count_evidence_links(
                evidence_links,
                VerificationVerdict.INSUFFICIENT_EVIDENCE,
            ),
            has_review=review_decision is not None,
            has_report_entry=review_decision is not None
            and not _is_excluded_from_report(review_decision),
        )

    def record_review(
        self,
        review_decision: ClaimReviewDecision,
    ) -> ClaimReviewDecision:
        """Persist a human review decision for report assembly."""

        return self.persistence.claims.save_review_decision(review_decision)

    def assemble_case_report(self, case_id: str) -> ReportAssemblyOutcome:
        """Assemble a report from the case's current claims and review state."""

        review_decisions = _review_decisions_for_case(self.persistence, case_id)
        return self.report_assembly.assemble_report(
            ReportAssemblyRequest(
                case_id=case_id,
                review_decisions=review_decisions,
            )
        )

    def assemble_continuity_pack(
        self,
        request: ContinuityPackRequest,
    ) -> ContinuityPackOutcome | None:
        """Assemble a decision-ready continuity pack from caller-provided sections."""

        if self.continuity_pack_execution is None:
            return None
        return self.continuity_pack_execution.assemble_pack(request)

    def inspect_continuity_pack(
        self,
        request: ContinuityPackRequest,
    ) -> ContinuityPackInspection | None:
        """Return an analyst-facing inspection view for continuity-pack sections."""

        outcome = self.assemble_continuity_pack(request)
        if outcome is None:
            return None
        continuity_pack = outcome.continuity_pack
        return ContinuityPackInspection(
            title=continuity_pack.title,
            source_artifact_path=continuity_pack.source_artifact_path,
            sections={
                CONTINUITY_PACK_SECTIONS[0]: continuity_pack.confirmed,
                CONTINUITY_PACK_SECTIONS[1]: continuity_pack.assumptions,
                CONTINUITY_PACK_SECTIONS[2]: continuity_pack.to_verify,
                CONTINUITY_PACK_SECTIONS[3]: continuity_pack.recommended_next_test,
            },
            decision_snapshot=continuity_pack.decision_snapshot,
        )

    def build_continuity_pack_from_artifact(
        self,
        artifact_path: str,
        *,
        title: str | None = None,
    ) -> ContinuityPackOutcome | None:
        """Build a continuity-pack preview directly from an existing repo artifact."""

        if self.continuity_pack_execution is None:
            return None
        request = build_continuity_pack_request_from_artifact(artifact_path, title=title)
        return self.continuity_pack_execution.assemble_pack(request)

    def assign_case_continuity_pack(
        self,
        case_id: str,
        *,
        artifact_path: str,
        title: str | None = None,
    ) -> ContinuityPackOutcome | None:
        """Build and persist the active continuity pack for an existing case."""

        if self.persistence.cases.get_case(case_id) is None:
            return None
        outcome = self.build_continuity_pack_from_artifact(artifact_path, title=title)
        if outcome is None:
            return None
        return self.persistence.cases.save_continuity_pack(case_id, outcome)

    def get_case_continuity_pack(self, case_id: str) -> ContinuityPackOutcome | None:
        """Return the active continuity pack for one case."""

        if self.persistence.cases.get_case(case_id) is None:
            return None
        return self.persistence.cases.get_continuity_pack(case_id)

    def get_latest_previous_case_continuity_pack(
        self,
        case_id: str,
    ) -> ContinuityPackOutcome | None:
        """Return the latest replaced continuity pack for one case."""

        if self.persistence.cases.get_case(case_id) is None:
            return None
        return self.persistence.cases.get_latest_previous_continuity_pack(case_id)

    def clear_case_continuity_pack(self, case_id: str) -> bool:
        """Remove the active continuity pack from one case."""

        if self.persistence.cases.get_case(case_id) is None:
            return False
        self.persistence.cases.clear_continuity_pack(case_id)
        return True

    def continuity_pack_persistence_status(self) -> ContinuityPackPersistenceStatus:
        """Return runtime diagnostics for continuity-pack persistence."""

        case_repository = self.persistence.cases
        if isinstance(case_repository, FileBackedCaseRepository):
            return case_repository.continuity_pack_persistence_status()
        return ContinuityPackPersistenceStatus(
            enabled=False,
            backend=case_repository.__class__.__name__,
            root_dir=None,
        )

    def render_continuity_pack_markdown(

        self,
        request: ContinuityPackRequest,
    ) -> str | None:
        """Render a continuity pack request as markdown preview."""

        outcome = self.assemble_continuity_pack(request)
        if outcome is None:
            return None
        return render_continuity_pack_markdown(outcome.continuity_pack)

    def render_continuity_pack_markdown_from_artifact(
        self,
        artifact_path: str,
        *,
        title: str | None = None,
    ) -> str | None:
        """Auto-build a continuity pack from a repo artifact and render markdown."""

        outcome = self.build_continuity_pack_from_artifact(artifact_path, title=title)
        if outcome is None:
            return None
        return render_continuity_pack_markdown(outcome.continuity_pack)

    def assess_document_credibility(
        self,
        document_id: str,
        *,
        assessment_method: str | None = None,
    ) -> CredibilityAssessmentOutcome | None:
        """Run the configured credibility assessment path for one stored document."""

        document = self.persistence.documents.get_document(document_id)
        if document is None or self.credibility_assessment is None:
            return None
        prepared_chunks = tuple(
            self.persistence.documents.list_chunks_for_document(document.case_id, document_id)
        )
        outcome = self.credibility_assessment.assess_credibility(
            CredibilityAssessmentRequest(
                document=document,
                assessment_method=assessment_method,
                prepared_chunks=prepared_chunks,
            )
        )
        assessment = self.persistence.documents.save_credibility_assessment(
            outcome.assessment
        )
        return CredibilityAssessmentOutcome(
            request=outcome.request,
            assessment=assessment,
        )

    def get_document_credibility(
        self,
        document_id: str,
    ) -> DocumentCredibilityAssessment | None:
        """Return the latest persisted credibility assessment for a document."""

        return self.persistence.documents.get_credibility_assessment(document_id)

    def readiness_payload(self) -> dict[str, object]:
        """Return minimal operational readiness metadata."""

        continuity_pack_persistence = self.continuity_pack_persistence_status()
        return {
            "status": "ready",
            "checks": {
                "delivery": True,
                "persistence": True,
                "verification_runtime": True,
                "claim_extraction": self.claim_extraction_runtime is not None,
                "continuity_pack": self.continuity_pack_execution is not None,
                "continuity_pack_persistence": continuity_pack_persistence.enabled,
                "credibility_assessment": self.credibility_assessment is not None,
            },
            "diagnostics": {
                "continuity_pack_persistence": {
                    "enabled": continuity_pack_persistence.enabled,
                    "backend": continuity_pack_persistence.backend,
                    "root_dir": continuity_pack_persistence.root_dir,
                }
            },
        }

    def runtime_payload(self) -> dict[str, object]:
        """Return delivery/runtime composition metadata."""

        continuity_pack_persistence = self.continuity_pack_persistence_status()
        return {
            "runtime": {
                "entrypoint": "wsgi",
                "storage": self.persistence.__class__.__name__,
                "verification_runtime": "enabled",
                "claim_extraction": _enabled(self.claim_extraction_runtime),
                "continuity_pack": _enabled(self.continuity_pack_execution),
                "continuity_pack_persistence": {
                    "enabled": continuity_pack_persistence.enabled,
                    "backend": continuity_pack_persistence.backend,
                    "root_dir": continuity_pack_persistence.root_dir,
                },
                "credibility_assessment": _enabled(self.credibility_assessment),
                "reporting": "enabled",
                "dev_routes": "enabled",
            }
        }

    def capabilities_payload(self) -> dict[str, object]:
        """Return supported HTTP resource and action capabilities."""

        return {
            "capabilities": {
                "cases": ["create", "list", "get"],
                "documents": ["create", "get", "list_for_case", "prepare", "chunks"],
                "claims": ["list_for_case", "get", "extract", "verify"],
                "evidence": ["list_for_claim"],
                "reviews": ["create", "get"],
                "continuity_packs": ["assemble_preview", "assemble_from_artifact", "render_markdown"],
                "credibility_assessments": ["create", "get"],
                "reports": ["get_json", "get_markdown"],
            },
            "runtime": {
                "claim_extraction": self.claim_extraction_runtime is not None,
                "credibility_assessment": self.credibility_assessment is not None,
            },
            "routes": {
                "product": [
                    "/api/cases",
                    "/api/cases/{case_id}",
                    "/api/cases/{case_id}/documents",
                    "/api/cases/{case_id}/claims",
                    "/api/documents/{document_id}",
                    "/api/documents/{document_id}/prepare",
                    "/api/documents/{document_id}/chunks",
                    "/api/documents/{document_id}/extract-claims",
                    "/api/documents/{document_id}/credibility",
                    "/api/claims/{claim_id}",
                    "/api/claims/{claim_id}/verification",
                    "/api/claims/{claim_id}/evidence",
                    "/api/claims/{claim_id}/review",
                    "/api/continuity-packs/assemble-preview",
                    "/api/continuity-packs/assemble-from-artifact",
                    "/api/continuity-packs/render-markdown",
                    "/api/reports/{case_id}",
                    "/api/reports/{case_id}.json",
                    "/api/reports/{case_id}.md",
                ],
                "dev": ["/api/dev/documents"],
                "html": ["/", "/cases/{case_id}"],
            },
        }

    def _remember_case_document(self, case: Case, document_id: str) -> None:
        if document_id in case.document_ids:
            return
        self.persistence.cases.save_case(
            replace(case, document_ids=case.document_ids + (document_id,))
        )

    def _remember_case_claims(
        self,
        case_id: str,
        claim_ids: tuple[str, ...],
    ) -> None:
        case = self.persistence.cases.get_case(case_id)
        if case is None:
            return
        new_claim_ids = tuple(
            claim_id
            for claim_id in claim_ids
            if claim_id not in case.claim_ids
        )
        if not new_claim_ids:
            return
        self.persistence.cases.save_case(
            replace(case, claim_ids=case.claim_ids + new_claim_ids)
        )

@dataclass(frozen=True)
class PersistenceReportAssembler:
    """Compose report entries from persisted claim, verification, and review state."""

    persistence: CorePersistence

    def __call__(self, request: ReportAssemblyRequest) -> ReportAssemblyOutcome:
        return self.assemble_report(request)

    def assemble_report(self, request: ReportAssemblyRequest) -> ReportAssemblyOutcome:
        entries = tuple(
            _report_entry_from_review(self.persistence, review_decision)
            for review_decision in request.review_decisions
            if not _is_excluded_from_report(review_decision)
        )
        case_report = CaseReport(
            case_id=request.case_id,
            generated_claim_ids=tuple(entry.claim_id for entry in entries),
            entries=entries,
            report_summary=_report_summary(entries),
        )
        return ReportAssemblyOutcome(
            request=request,
            entries=entries,
            case_report=case_report,
        )


@dataclass(frozen=True)
class ContinuityPackAssemblerRuntime:
    """Assemble caller-provided continuity-pack sections into a stable artifact."""

    def __call__(self, request: ContinuityPackRequest) -> ContinuityPackOutcome:
        continuity_pack = ContinuityPack(
            title=request.title,
            source_artifact_path=request.source_artifact_path,
            confirmed=tuple(item.strip() for item in request.confirmed if item.strip()),
            assumptions=tuple(item.strip() for item in request.assumptions if item.strip()),
            to_verify=tuple(item.strip() for item in request.to_verify if item.strip()),
            recommended_next_test=tuple(
                item.strip() for item in request.recommended_next_test if item.strip()
            ),
            decision_snapshot=tuple(
                item.strip() for item in request.decision_snapshot if item.strip()
            ),
        )
        return ContinuityPackOutcome(
            request=request,
            continuity_pack=continuity_pack,
        )


def _report_entry_from_review(
    persistence: CorePersistence,
    decision: ClaimReviewDecision,
) -> ClaimReportEntry:
    claim = persistence.claims.get_claim(decision.claim_id)
    verification = _get_verification(persistence, decision.claim_id)
    final_verdict = (
        decision.final_verdict
        or (verification.verdict if verification is not None else None)
        or (claim.system_verdict if claim is not None else None)
        or VerificationVerdict.INSUFFICIENT_EVIDENCE
    )
    return ClaimReportEntry(
        claim_id=decision.claim_id,
        case_id=decision.case_id,
        final_verdict=final_verdict,
        human_review_status=decision.human_review_status,
        summary_text=_entry_summary(decision, claim, final_verdict),
        supporting_chunk_ids=(
            verification.supporting_chunk_ids if verification is not None else ()
        ),
        contradicting_chunk_ids=(
            verification.contradicting_chunk_ids if verification is not None else ()
        ),
    )


def create_default_delivery(
    persistence: CorePersistence | None = None,
    credibility_draft: "CredibilityDraftGateway | None" = None,
    credibility_assessed_at: Callable[[], datetime] | None = None,
    claim_extraction: "ClaimExtractionGateway | None" = None,
    claim_normalization: "ClaimNormalizationGateway | None" = None,
    claim_extraction_runtime: ClaimExtractionRuntime | None = None,
    continuity_pack_root_dir: str | Path | None = None,
) -> SourceTraceDelivery:
    """Create the default analyst delivery surface."""

    if persistence is None:
        persistence = create_in_memory_persistence()
        if continuity_pack_root_dir is not None:
            persistence = CorePersistence(
                cases=FileBackedCaseRepository(continuity_pack_root_dir),
                documents=persistence.documents,
                claims=persistence.claims,
            )
    verification_runtime = ClaimVerificationRuntime(
        persistence=persistence,
        retrieval=RetrievalExecution(
            retrieve_chunks=LexicalChunkRetriever(documents=persistence.documents)
        ),
        verification=ClaimVerificationExecution(
            verify_claim=EvidencePresenceClaimVerifier()
        ),
    )
    report_assembly = ReportAssemblyExecution(
        assemble_report=PersistenceReportAssembler(persistence=persistence)
    )
    continuity_pack_execution = ContinuityPackExecution(
        assemble_pack=ContinuityPackAssemblerRuntime()
    )
    credibility_assessment = _build_credibility_assessment_execution(
        credibility_draft=credibility_draft,
        credibility_assessed_at=credibility_assessed_at,
    )
    claim_extraction_runtime = claim_extraction_runtime or _build_claim_extraction_runtime(
        claim_extraction=claim_extraction,
        claim_normalization=claim_normalization,
    )
    return SourceTraceDelivery(
        persistence=persistence,
        verification_runtime=verification_runtime,
        report_assembly=report_assembly,
        continuity_pack_execution=continuity_pack_execution,
        credibility_assessment=credibility_assessment,
        claim_extraction_runtime=claim_extraction_runtime,
    )


def continuity_pack_summary_to_payload(
    continuity_pack: ContinuityPackOutcome | None,
    *,
    latest_previous: ContinuityPackOutcome | None = None,
    include_latest_previous: bool = True,
) -> dict[str, object]:
    """Serialize current continuity-pack assignment summary for case payloads."""

    summary: dict[str, object]
    if continuity_pack is None:
        summary = {
            "assigned": False,
            "title": None,
            "source_artifact_path": None,
        }
    else:
        pack = continuity_pack.continuity_pack
        summary = {
            "assigned": True,
            "title": pack.title,
            "source_artifact_path": pack.source_artifact_path,
        }
    if include_latest_previous:
        summary["latest_previous"] = continuity_pack_summary_to_payload(
            latest_previous,
            include_latest_previous=False,
        )
    return summary


def case_to_payload(
    case: Case,
    *,
    continuity_pack: ContinuityPackOutcome | None = None,
    latest_previous_continuity_pack: ContinuityPackOutcome | None = None,
) -> dict[str, object]:
    """Serialize a case for JSON API responses."""

    payload = {
        "case_id": case.case_id,
        "title": case.title,
        "description": case.description,
        "document_ids": list(case.document_ids),
        "claim_ids": list(case.claim_ids),
        "continuity_pack": continuity_pack_summary_to_payload(
            continuity_pack,
            latest_previous=latest_previous_continuity_pack,
        ),
    }
    return payload


def chunk_to_payload(chunk: DocumentChunk) -> dict[str, object]:
    """Serialize a document chunk for JSON API responses."""

    return {
        "chunk_id": chunk.chunk_id,
        "case_id": chunk.case_id,
        "document_id": chunk.document_id,
        "raw_text": chunk.raw_text,
        "start_char": chunk.start_char,
        "end_char": chunk.end_char,
        "chunk_index": chunk.chunk_index,
        "position_reference": chunk.position_reference,
        "previous_chunk_id": chunk.previous_chunk_id,
        "next_chunk_id": chunk.next_chunk_id,
    }


def review_decision_to_payload(
    review_decision: ClaimReviewDecision,
) -> dict[str, object]:
    """Serialize a human review decision for JSON API responses."""

    return {
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


def document_preparation_outcome_to_payload(
    outcome: DocumentPreparationOutcome,
) -> dict[str, object]:
    """Serialize a document preparation outcome for JSON API responses."""

    document_payload = document_to_payload(outcome.document)
    diagnostics = _prepare_diagnostics(outcome)
    return {
        "status": diagnostics["status"],
        "summary": diagnostics["summary"],
        "next_step": diagnostics["next_step"],
        "resource": "document_preparation",
        "resource_id": outcome.document.document_id,
        "document": document_payload,
        "document_id": document_payload["document_id"],
        "chunks": [chunk_to_payload(chunk) for chunk in outcome.chunks],
        "diagnostics": diagnostics,
    }


def claim_extraction_outcome_to_payload(
    outcome: ClaimExtractionOutcome,
) -> dict[str, object]:
    """Serialize a claim extraction outcome for JSON API responses."""

    document_payload = document_to_payload(outcome.document)
    diagnostics = _claim_extraction_diagnostics(outcome)
    return {
        "status": diagnostics["status"],
        "summary": diagnostics["summary"],
        "next_step": diagnostics["next_step"],
        "resource": "claim_extraction",
        "resource_id": outcome.document.document_id,
        "document": document_payload,
        "document_id": document_payload["document_id"],
        "chunks": [chunk_to_payload(chunk) for chunk in outcome.chunks],
        "claims": [claim_to_payload(claim) for claim in outcome.claims],
        "evidence_links": [
            evidence_link_to_payload(link) for link in outcome.evidence_links
        ],
        "diagnostics": diagnostics,
    }


def verification_inspection_to_payload(
    inspection: VerificationInspection,
) -> dict[str, object]:
    """Serialize an analyst-facing verification inspection view."""

    return {
        "claim": claim_to_payload(inspection.claim),
        "verification": verification_to_payload(inspection.verification),
        "evidence_links": [
            evidence_link_to_payload(link) for link in inspection.evidence_links
        ],
        "evidence_summary": {
            "evidence_count": inspection.evidence_count,
            "supporting_evidence_count": inspection.supporting_evidence_count,
            "contradicting_evidence_count": inspection.contradicting_evidence_count,
            "insufficient_evidence_count": inspection.insufficient_evidence_count,
            "has_review": inspection.has_review,
            "has_report_entry": inspection.has_report_entry,
        },
    }


def continuity_pack_to_payload(
    continuity_pack: ContinuityPack,
) -> dict[str, object]:
    """Serialize a continuity-pack artifact for JSON API responses."""

    return {
        "title": continuity_pack.title,
        "source_artifact_path": continuity_pack.source_artifact_path,
        "confirmed": list(continuity_pack.confirmed),
        "assumptions": list(continuity_pack.assumptions),
        "to_verify": list(continuity_pack.to_verify),
        "recommended_next_test": list(continuity_pack.recommended_next_test),
        "decision_snapshot": list(continuity_pack.decision_snapshot),
    }


def continuity_pack_read_payload(
    *,
    case_id: str,
    active: ContinuityPackOutcome | None,
    latest_previous: ContinuityPackOutcome | None,
) -> dict[str, object]:
    """Serialize the continuity-pack read model for one case."""

    return {
        "status": "ready",
        "resource": "case_continuity_pack",
        "resource_id": case_id,
        "case_id": case_id,
        "continuity_pack": continuity_pack_summary_to_payload(
            active,
            latest_previous=latest_previous,
        ),
        "artifacts": {
            "active": active.request.source_artifact_path if active is not None else None,
            "latest_previous": (
                latest_previous.request.source_artifact_path
                if latest_previous is not None
                else None
            ),
        },
        "actions": {
            "assign": f"/api/cases/{case_id}/continuity-pack",
            "clear": f"/api/cases/{case_id}/continuity-pack",
            "view_active": (
                f"/continuity-packs/view?artifact_path={url_quote(active.request.source_artifact_path)}"
                if active is not None
                else None
            ),
            "view_latest_previous": (
                f"/continuity-packs/view?artifact_path={url_quote(latest_previous.request.source_artifact_path)}"
                if latest_previous is not None
                else None
            ),
        },
    }


def continuity_pack_outcome_to_payload(
    outcome: ContinuityPackOutcome,
) -> dict[str, object]:
    """Serialize a continuity-pack assembly outcome for JSON API responses."""

    continuity_pack_payload = continuity_pack_to_payload(outcome.continuity_pack)
    return {
        "status": "ready",
        "summary": "Continuity pack assembled from the provided artifact sections.",
        "next_step": "Review the continuity pack and decide whether to park, execute, or escalate.",
        "resource": "continuity_pack",
        "resource_id": outcome.request.source_artifact_path,
        "continuity_pack": continuity_pack_payload,
    }


def continuity_pack_inspection_to_payload(
    inspection: ContinuityPackInspection,
) -> dict[str, object]:
    """Serialize an analyst-facing continuity-pack inspection view."""

    return {
        "title": inspection.title,
        "source_artifact_path": inspection.source_artifact_path,
        "sections": {name: list(items) for name, items in inspection.sections.items()},
        "decision_snapshot": list(inspection.decision_snapshot),
    }


def verification_outcome_to_payload(
    outcome: ClaimVerificationRuntimeOutcome,
) -> dict[str, object]:
    """Serialize a verification runtime outcome for JSON responses."""

    return {
        "retrieval_query": {
            "query_id": outcome.retrieval_query.query_id,
            "case_id": outcome.retrieval_query.case_id,
            "query_text": outcome.retrieval_query.query_text,
            "requested_k": outcome.retrieval_query.requested_k,
            "retrieval_method": outcome.retrieval_query.retrieval_method,
            "document_ids": list(outcome.retrieval_query.document_ids),
        },
        "retrieved_evidence": {
            "query_id": outcome.retrieved_evidence.query_id,
            "case_id": outcome.retrieved_evidence.case_id,
            "returned_k": outcome.retrieved_evidence.returned_k,
            "retrieval_method": outcome.retrieved_evidence.retrieval_method,
            "hits": [
                {
                    "case_id": hit.case_id,
                    "document_id": hit.document_id,
                    "chunk_id": hit.chunk_id,
                    "rank": hit.rank,
                    "snippet": hit.snippet,
                    "score": hit.score,
                    "query_text": hit.query_text,
                    "retrieval_method": hit.retrieval_method,
                }
                for hit in outcome.retrieved_evidence.hits
            ],
        },
        "verification": verification_to_payload(
            outcome.verification_outcome.verification
        ),
        "evidence_links": [
            evidence_link_to_payload(link) for link in outcome.evidence_links
        ],
    }


def report_outcome_to_payload(outcome: ReportAssemblyOutcome) -> dict[str, object]:
    """Serialize a case report for JSON responses."""

    return {
        "case_report": {
            "case_id": outcome.case_report.case_id,
            "generated_claim_ids": list(outcome.case_report.generated_claim_ids),
            "report_summary": outcome.case_report.report_summary,
            "entries": [report_entry_to_payload(entry) for entry in outcome.entries],
        }
    }


def document_credibility_assessment_to_payload(
    assessment: DocumentCredibilityAssessment,
) -> dict[str, object]:
    """Serialize a document credibility assessment for JSON responses."""

    payload = {
        "assessment_id": assessment.assessment_id,
        "document_id": assessment.document_id,
        "source_reliability": assessment.source_reliability.value,
        "information_credibility": assessment.information_credibility.value,
        "source_reliability_factors": list(assessment.source_reliability_factors),
        "information_credibility_factors": list(
            assessment.information_credibility_factors
        ),
        "provenance_distance": assessment.provenance_distance.value,
        "method": assessment.method,
        "notes": assessment.notes,
        "summary": assessment.summary,
        "strengths": list(assessment.strengths),
        "concerns": list(assessment.concerns),
        "verification_checks": list(assessment.verification_checks),
        "assessed_by": assessment.assessed_by,
        "assessed_at": assessment.assessed_at.isoformat(),
        "override": assessment.override,
    }
    return payload


def credibility_assessment_response_payload(
    assessment: DocumentCredibilityAssessment,
) -> dict[str, object]:
    assessment_payload = document_credibility_assessment_to_payload(assessment)
    return {
        "status": "ready",
        "summary": "Credibility assessment is available.",
        "next_step": f"GET /api/documents/{assessment.document_id}/credibility",
        "resource": "document_credibility",
        "resource_id": assessment.document_id,
        "document_id": assessment.document_id,
        "credibility_assessment": assessment_payload,
    }


def render_case_review_html(delivery: SourceTraceDelivery, case_id: str) -> str:
    """Render a tiny server-side analyst view for one case."""

    case = delivery.persistence.cases.get_case(case_id)
    if case is None:
        return (
            "<!doctype html>"
            "<html><head><title>SourceTrace Case Review</title></head>"
            "<body>"
            "<h1>Case not found</h1>"
            f"<p><strong>Case ID:</strong> {_escape_html(case_id)}</p>"
            "<p>The requested case does not exist.</p>"
            "</body></html>"
        )

    documents = delivery.persistence.documents.list_documents_for_case(case_id)
    claims = delivery.persistence.claims.list_claims_for_case(case_id)
    claim_rows = "\n".join(_claim_row_html(delivery, claim) for claim in claims)
    if not claim_rows:
        claim_rows = '<tr><td colspan="4">No claims available.</td></tr>'
    document_rows = "\n".join(
        _case_document_row_html(delivery, document) for document in documents
    )
    if not document_rows:
        document_rows = (
            '<tr><td colspan="7">No documents attached yet. Create a document, then '
            "run prepare/extract/credibility.</td></tr>"
        )
    continuity_pack = delivery.get_case_continuity_pack(case_id)
    latest_previous_continuity_pack = delivery.get_latest_previous_case_continuity_pack(case_id)
    continuity_pack_section = _case_continuity_pack_section_html(
        continuity_pack,
        latest_previous_continuity_pack=latest_previous_continuity_pack,
    ).replace("{case_id}", _escape_html(case_id))
    case_title = _escape_html(case.title)
    case_description = _escape_html(case.description or "No case description provided yet.")
    return (
        "<!doctype html>"
        "<html><head><title>SourceTrace Case Review</title></head>"
        "<body>"
        f"<h1>Case {case_title}</h1>"
        f"<p><strong>Case ID:</strong> {_escape_html(case_id)}</p>"
        f"<p>{case_description}</p>"
        f"<p><strong>Documents:</strong> {len(documents)} &middot; <strong>Claims:</strong> {len(claims)}</p>"
        f"{continuity_pack_section}"
        "<h2>Document status</h2>"
        "<table>"
        "<thead><tr><th>Document</th><th>Source type</th><th>Chunks</th><th>Claims</th><th>Credibility</th><th>Status</th><th>Next action</th></tr></thead>"
        f"<tbody>{document_rows}</tbody>"
        "</table>"
        "<h2>Claims</h2>"
        "<table>"
        "<thead><tr><th>Claim</th><th>Verdict</th><th>Review</th>"
        "<th>Evidence</th></tr></thead>"
        f"<tbody>{claim_rows}</tbody>"
        "</table>"
        "</body></html>"
    )


def render_report_markdown(outcome: ReportAssemblyOutcome) -> str:
    """Render a minimal Markdown report artifact."""

    lines = [
        f"# SourceTrace Report: {outcome.case_report.case_id}",
        "",
        outcome.case_report.report_summary or "No report entries.",
        "",
    ]
    for entry in outcome.entries:
        lines.extend(
            [
                f"## {entry.claim_id}",
                "",
                f"- Final verdict: {entry.final_verdict.value}",
                f"- Human review: {entry.human_review_status.value}",
                f"- Summary: {entry.summary_text}",
                f"- Supporting chunks: {_format_chunk_ids(entry.supporting_chunk_ids)}",
                "- Contradicting chunks: "
                f"{_format_chunk_ids(entry.contradicting_chunk_ids)}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_continuity_pack_html(
    delivery: SourceTraceDelivery,
    *,
    artifact_path: str,
    title: str | None = None,
) -> str:
    """Render a small HTML continuity-pack view from an existing artifact."""

    outcome = delivery.build_continuity_pack_from_artifact(artifact_path, title=title)
    if outcome is None:
        raise ValueError("continuity pack capability is not available.")
    pack = outcome.continuity_pack
    return (
        "<!doctype html>"
        "<html><head><title>SourceTrace Continuity Pack</title></head>"
        "<body>"
        f"<h1>{_escape_html(pack.title)}</h1>"
        f"<p><strong>Source artifact:</strong> {_escape_html(pack.source_artifact_path)}</p>"
        f"<h2>{_escape_html(CONTINUITY_PACK_SECTIONS[0])}</h2>"
        f"{_continuity_pack_list_html(pack.confirmed)}"
        f"<h2>{_escape_html(CONTINUITY_PACK_SECTIONS[1])}</h2>"
        f"{_continuity_pack_list_html(pack.assumptions)}"
        f"<h2>{_escape_html(CONTINUITY_PACK_SECTIONS[2])}</h2>"
        f"{_continuity_pack_list_html(pack.to_verify)}"
        f"<h2>{_escape_html(CONTINUITY_PACK_SECTIONS[3])}</h2>"
        f"{_continuity_pack_list_html(pack.recommended_next_test)}"
        "<h2>Decision snapshot</h2>"
        f"{_continuity_pack_list_html(pack.decision_snapshot)}"
        "</body></html>"
    )


def case_creation_request_from_payload(
    payload: dict[str, object],
) -> CaseCreationRequest:
    """Deserialize a case creation payload."""

    case_id = str(payload.get("case_id") or "").strip()
    title = str(payload.get("title") or "").strip()
    if not title:
        raise ValueError("title is required.")
    if not case_id:
        case_id = f"case-{uuid4().hex[:8]}"
    return CaseCreationRequest(
        case_id=case_id,
        title=title,
        description=_optional_str(payload.get("description")),
    )


def claim_from_payload(payload: dict[str, object]) -> Claim:
    """Deserialize a claim from an API payload."""

    return Claim(
        claim_id=str(payload["claim_id"]),
        case_id=str(payload["case_id"]),
        document_id=str(payload["document_id"]),
        chunk_id=_optional_str(payload.get("chunk_id")),
        exact_text=str(payload["exact_text"]),
        source_span_reference=str(payload["source_span_reference"]),
        system_verdict=VerificationVerdict(
            str(
                payload.get(
                    "system_verdict",
                    VerificationVerdict.INSUFFICIENT_EVIDENCE.value,
                )
            )
        ),
        rationale=_optional_str(payload.get("rationale")),
    )


def review_decision_from_payload(payload: dict[str, object]) -> ClaimReviewDecision:
    """Deserialize a review decision from an API payload."""

    if "claim_id" not in payload:
        raise ValueError("claim_id is required.")
    if "case_id" not in payload:
        raise ValueError("case_id is required.")
    if "human_review_status" not in payload:
        raise ValueError("human_review_status is required.")

    final_verdict = payload.get("final_verdict")
    analyst_disposition = payload.get("analyst_disposition")
    return ClaimReviewDecision(
        claim_id=str(payload["claim_id"]),
        case_id=str(payload["case_id"]),
        human_review_status=HumanReviewStatus(str(payload["human_review_status"])),
        analyst_disposition=(
            AnalystDisposition(str(analyst_disposition))
            if analyst_disposition is not None
            else None
        ),
        final_verdict=(
            VerificationVerdict(str(final_verdict))
            if final_verdict is not None
            else None
        ),
        review_notes=_optional_str(payload.get("review_notes")),
    )


def claim_to_payload(claim: Claim) -> dict[str, object]:
    """Serialize a claim for API responses."""

    if os.getenv("SOURCETRACE_DEBUG_CLAIM_PIPELINE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        print(
            "[sourcetrace.claim-debug] "
            "stage=response_claim_payload "
            f"claim_id={claim.claim_id!r} "
            f"case_id={claim.case_id!r} "
            f"document_id={claim.document_id!r} "
            f"exact_text={claim.exact_text!r}",
            flush=True,
        )

    return {
        "claim_id": claim.claim_id,
        "case_id": claim.case_id,
        "document_id": claim.document_id,
        "chunk_id": claim.chunk_id,
        "exact_text": claim.exact_text,
        "source_span_reference": claim.source_span_reference,
        "system_verdict": claim.system_verdict.value,
        "rationale": claim.rationale,
    }


def verification_to_payload(
    verification: ClaimVerification,
) -> dict[str, object]:
    """Serialize a claim verification for API responses."""

    return {
        "claim_id": verification.claim_id,
        "case_id": verification.case_id,
        "verdict": verification.verdict.value,
        "supporting_chunk_ids": list(verification.supporting_chunk_ids),
        "contradicting_chunk_ids": list(verification.contradicting_chunk_ids),
        "analyst_notes": verification.analyst_notes,
    }


def evidence_link_to_payload(link: ClaimEvidenceLink) -> dict[str, object]:
    """Serialize a claim evidence link for API responses."""

    return {
        "claim_id": link.claim_id,
        "document_id": link.document_id,
        "chunk_id": link.chunk_id,
        "evidence_rank": link.evidence_rank,
        "evidence_verdict": link.evidence_verdict.value,
        "rationale": link.rationale,
        "snippet": link.snippet,
        "score": link.score,
    }


def report_entry_to_payload(entry: ClaimReportEntry) -> dict[str, object]:
    """Serialize a report entry for API responses."""

    return {
        "claim_id": entry.claim_id,
        "case_id": entry.case_id,
        "final_verdict": entry.final_verdict.value,
        "human_review_status": entry.human_review_status.value,
        "summary_text": entry.summary_text,
        "supporting_chunk_ids": list(entry.supporting_chunk_ids),
        "contradicting_chunk_ids": list(entry.contradicting_chunk_ids),
    }


def _review_decisions_for_case(
    persistence: CorePersistence,
    case_id: str,
) -> tuple[ClaimReviewDecision, ...]:
    decisions: list[ClaimReviewDecision] = []
    for claim in persistence.claims.list_claims_for_case(case_id):
        decision = _get_review_decision(persistence, claim.claim_id)
        if decision is None:
            verification = _get_verification(persistence, claim.claim_id)
            decision = ClaimReviewDecision(
                claim_id=claim.claim_id,
                case_id=claim.case_id,
                human_review_status=HumanReviewStatus.UNREVIEWED,
                final_verdict=(
                    verification.verdict
                    if verification is not None
                    else claim.system_verdict
                ),
            )
        decisions.append(decision)
    return tuple(decisions)


def _build_credibility_assessment_execution(
    *,
    credibility_draft: "CredibilityDraftGateway | None",
    credibility_assessed_at: Callable[[], datetime] | None,
) -> CredibilityAssessmentExecution | None:
    if credibility_draft is None:
        return None
    return CredibilityAssessmentExecution(
        assess_credibility=build_llm_credibility_assessor(
            draft_credibility=credibility_draft,
            assessed_at=credibility_assessed_at,
        )
    )


def _build_claim_extraction_runtime(
    *,
    claim_extraction: "ClaimExtractionGateway | None",
    claim_normalization: "ClaimNormalizationGateway | None",
) -> ClaimExtractionRuntime | None:
    if claim_extraction is None:
        return None
    return ClaimExtractionRuntime(
        extract_claims=build_llm_claim_extractor(
            extract_claims=claim_extraction,
            normalize_claim=claim_normalization,
        )
    )


def _get_verification(
    persistence: CorePersistence,
    claim_id: str,
) -> ClaimVerification | None:
    get_verification = getattr(persistence.claims, "get_verification", None)
    if not callable(get_verification):
        return None
    return get_verification(claim_id)


def _get_review_decision(
    persistence: CorePersistence,
    claim_id: str,
) -> ClaimReviewDecision | None:
    get_review_decision = getattr(persistence.claims, "get_review_decision", None)
    if not callable(get_review_decision):
        return None
    return get_review_decision(claim_id)


def _list_evidence_links(
    persistence: CorePersistence,
    claim_id: str,
) -> tuple[ClaimEvidenceLink, ...]:
    list_links = getattr(persistence.claims, "list_evidence_links_for_claim", None)
    if not callable(list_links):
        return ()
    return tuple(list_links(claim_id))


def _chunks_from_text(
    *,
    case_id: str,
    document_id: str,
    raw_text: str,
) -> tuple[DocumentChunk, ...]:
    blocks = _text_blocks(raw_text)
    chunks: list[DocumentChunk] = []
    search_from = 0
    for index, block in enumerate(blocks, start=1):
        start_char = raw_text.find(block, search_from)
        if start_char < 0:
            start_char = search_from
        end_char = start_char + len(block)
        chunk_id = f"{document_id}:chunk-{index}"
        chunks.append(
            DocumentChunk(
                chunk_id=chunk_id,
                case_id=case_id,
                document_id=document_id,
                raw_text=block,
                start_char=start_char,
                end_char=end_char,
                chunk_index=index - 1,
                position_reference=f"p{index}",
                previous_chunk_id=(
                    f"{document_id}:chunk-{index - 1}" if index > 1 else None
                ),
                next_chunk_id=(
                    f"{document_id}:chunk-{index + 1}"
                    if index < len(blocks)
                    else None
                ),
            )
        )
        search_from = end_char
    return tuple(chunks)


def _text_blocks(raw_text: str) -> tuple[str, ...]:
    blocks = tuple(block.strip() for block in raw_text.split("\n\n") if block.strip())
    if blocks:
        return blocks
    stripped = raw_text.strip()
    return (stripped,) if stripped else ()


def _enabled(value: object | None) -> str:
    return "enabled" if value is not None else "disabled"


def _count_evidence_links(
    evidence_links: tuple[ClaimEvidenceLink, ...],
    verdict: VerificationVerdict,
) -> int:
    return sum(1 for link in evidence_links if link.evidence_verdict is verdict)


def _is_excluded_from_report(decision: ClaimReviewDecision) -> bool:
    return (
        decision.human_review_status is HumanReviewStatus.EXCLUDED
        or decision.analyst_disposition is AnalystDisposition.EXCLUDE_FROM_REPORT
    )


def _entry_summary(
    decision: ClaimReviewDecision,
    claim: Claim | None,
    final_verdict: VerificationVerdict,
) -> str:
    if decision.review_notes:
        return decision.review_notes
    if claim is not None:
        return claim.exact_text
    return f"Claim {decision.claim_id} resolved as {final_verdict.value}."


def _report_summary(entries: tuple[ClaimReportEntry, ...]) -> str:
    if len(entries) == 1:
        return "1 claim included in this report."
    return f"{len(entries)} claims included in this report."


def _claim_row_html(delivery: SourceTraceDelivery, claim: Claim) -> str:
    verification = _get_verification(delivery.persistence, claim.claim_id)
    review = _get_review_decision(delivery.persistence, claim.claim_id)
    links = _list_evidence_links(delivery.persistence, claim.claim_id)
    verdict = _display_verdict(claim, verification)
    review_status = (
        review.human_review_status.value if review is not None else "unreviewed"
    )
    evidence_count = str(len(links))
    claim_links = [
        f'<a href="/api/claims/{claim.claim_id}">claim</a>',
        f'<a href="/api/claims/{claim.claim_id}/evidence">evidence</a>',
    ]
    verification_link = f'/api/claims/{claim.claim_id}/verification'
    claim_links.append(f'<a href="{verification_link}">verification</a>')
    return (
        "<tr>"
        f"<td>{_escape_html(claim.exact_text)}<br><small>{' · '.join(claim_links)}</small></td>"
        f"<td>{_escape_html(verdict)}</td>"
        f"<td>{_escape_html(review_status)}</td>"
        f"<td>{evidence_count}</td>"
        "</tr>"
    )


def _continuity_pack_list_html(items: tuple[str, ...]) -> str:
    if not items:
        return "<ul><li>None.</li></ul>"
    return "<ul>" + "".join(f"<li>{_escape_html(item)}</li>" for item in items) + "</ul>"


def _suggested_continuity_pack_artifacts_html(
    *,
    replace: bool,
) -> str:
    suggestions = _discover_continuity_pack_artifact_paths()
    if not suggestions:
        return ""
    action_label = "Replace with" if replace else "Assign"
    intro = (
        "<p><strong>Suggested replacement continuity-pack artifacts:</strong></p>"
        if replace
        else "<p><strong>Suggested continuity-pack artifacts:</strong></p>"
    )
    items = []
    for artifact_path in suggestions:
        href = (
            "/cases/assign-continuity-pack?case_id={case_id}&artifact_path="
            f"{url_quote(artifact_path)}"
        )
        label = _escape_html(Path(artifact_path).name)
        items.append(
            f'<li><a href="{_escape_html(href)}">{action_label} {label}</a></li>'
        )
    return intro + f"<ul>{''.join(items)}</ul>"


def _discover_continuity_pack_artifact_paths() -> tuple[str, ...]:
    docs_plans_dir = Path(__file__).resolve().parents[3] / "docs" / "plans"
    if not docs_plans_dir.exists():
        return ()
    suggestions: list[str] = []
    for path in sorted(docs_plans_dir.glob("*continuity-pack*.md")):
        relative_path = path.relative_to(Path(__file__).resolve().parents[3]).as_posix()
        if "usage-note" in path.name or "broken-" in path.name:
            continue
        suggestions.append(relative_path)
    return tuple(suggestions)


def _case_continuity_pack_section_html(
    continuity_pack: ContinuityPackOutcome | None,
    *,
    latest_previous_continuity_pack: ContinuityPackOutcome | None = None,
) -> str:
    if continuity_pack is None:
        suggested_artifacts_html = _suggested_continuity_pack_artifacts_html(replace=False)
        return (
            "<h2>Continuity pack</h2>"
            "<p>No active continuity pack for this case yet.</p>"
            "<p><strong>Next step:</strong> "
            "POST /api/cases/{case_id}/continuity-pack with an artifact_path from "
            "<code>docs/plans/...continuity-pack...</code>.</p>"
            f"{suggested_artifacts_html}"
        )
    pack = continuity_pack.continuity_pack
    previous_pack = (
        latest_previous_continuity_pack.continuity_pack
        if latest_previous_continuity_pack is not None
        else None
    )
    suggested_replacements_html = _suggested_continuity_pack_artifacts_html(replace=True)
    clear_href = f"/cases/clear-continuity-pack?case_id={{case_id}}"
    view_href = f"/continuity-packs/view?artifact_path={url_quote(pack.source_artifact_path)}"
    render_href = "/api/continuity-packs/render-markdown?artifact_path="
    render_href += url_quote(pack.source_artifact_path)
    latest_previous_html = ""
    if previous_pack is not None:
        previous_view_href = (
            f"/continuity-packs/view?artifact_path={url_quote(previous_pack.source_artifact_path)}"
        )
        previous_assign_href = (
            "/cases/assign-continuity-pack?case_id={case_id}&artifact_path="
            f"{url_quote(previous_pack.source_artifact_path)}"
        )
        latest_previous_html = (
            "<h3>Latest previous continuity pack</h3>"
            f"<p><strong>Title:</strong> {_escape_html(previous_pack.title)}</p>"
            f"<p><strong>Source artifact:</strong> <code>{_escape_html(previous_pack.source_artifact_path)}</code></p>"
            f"<p><a href=\"{_escape_html(previous_view_href)}\">Open previous continuity-pack view</a>"
            " &middot; "
            f"<a href=\"{_escape_html(previous_assign_href)}\">Reassign previous continuity pack</a></p>"
        )
    return (
        "<h2>Continuity pack</h2>"
        f"<p><strong>Title:</strong> {_escape_html(pack.title)}</p>"
        f"<p><strong>Source artifact:</strong> <code>{_escape_html(pack.source_artifact_path)}</code></p>"
        "<p><strong>Replace warning:</strong> assigning another continuity pack will replace the current active pack for this case.</p>"
        f"<p><a href=\"{_escape_html(view_href)}\">Open dedicated continuity-pack view</a>"
        " &middot; "
        f"<a href=\"{_escape_html(render_href)}\">Render markdown</a>"
        " &middot; "
        f"<a href=\"{_escape_html(clear_href)}\">Clear active continuity pack</a></p>"
        f"{latest_previous_html}"
        f"{suggested_replacements_html}"
        f"<h3>{_escape_html(CONTINUITY_PACK_SECTIONS[0])}</h3>"
        f"{_continuity_pack_list_html(pack.confirmed)}"
        f"<h3>{_escape_html(CONTINUITY_PACK_SECTIONS[1])}</h3>"
        f"{_continuity_pack_list_html(pack.assumptions)}"
        f"<h3>{_escape_html(CONTINUITY_PACK_SECTIONS[2])}</h3>"
        f"{_continuity_pack_list_html(pack.to_verify)}"
        f"<h3>{_escape_html(CONTINUITY_PACK_SECTIONS[3])}</h3>"
        f"{_continuity_pack_list_html(pack.recommended_next_test)}"
        "<h3>Decision snapshot</h3>"
        f"{_continuity_pack_list_html(pack.decision_snapshot)}"
    )


def _display_verdict(
    claim: Claim,
    verification: ClaimVerification | None,
) -> str:
    if verification is not None:
        return verification.verdict.value
    return claim.system_verdict.value


def _case_document_row_html(delivery: SourceTraceDelivery, document: Document) -> str:
    chunks = delivery.persistence.documents.list_chunks_for_document(
        document.case_id,
        document.document_id,
    )
    claims = tuple(
        claim
        for claim in delivery.persistence.claims.list_claims_for_case(document.case_id)
        if claim.document_id == document.document_id
    )
    assessment = delivery.persistence.documents.get_credibility_assessment(
        document.document_id
    )
    status_parts: list[str] = []
    status_parts.append("prepared" if chunks else "not prepared")
    status_parts.append("claims extracted" if claims else "no claims yet")
    status_parts.append(
        "credibility drafted" if assessment is not None else "no credibility yet"
    )
    if not chunks:
        next_action = f"POST /api/documents/{document.document_id}/prepare"
    elif not claims:
        next_action = f"POST /api/documents/{document.document_id}/extract-claims"
    elif assessment is None:
        next_action = f"POST /api/documents/{document.document_id}/credibility"
    else:
        next_action = f"GET /api/documents/{document.document_id}/credibility"
    credibility_text = (
        assessment.information_credibility.value
        if assessment is not None
        else "not_assessed"
    )
    credibility_detail = _credibility_html_summary(assessment)
    if assessment is None:
        credibility_detail = (
            '<div class="credibility-state"><strong>Status:</strong> '
            'Not assessed yet.</div>'
            '<div class="credibility-state-next"><strong>Next step:</strong> '
            f'<code>{_escape_html(f"POST /api/documents/{document.document_id}/credibility")}</code></div>'
        )
    title = _escape_html(document.title or document.document_id)
    snippet_html = _document_snippet_html(document, chunks)
    return (
        "<tr>"
        f"<td>{title}<br><small>{_escape_html(document.document_id)}</small>{snippet_html}</td>"
        f"<td>{_escape_html(document.source_type)}</td>"
        f"<td>{len(chunks)}</td>"
        f"<td>{len(claims)}</td>"
        f"<td>{_escape_html(credibility_text)}{credibility_detail}</td>"
        f"<td>{_escape_html(', '.join(status_parts))}</td>"
        f"<td><code>{_escape_html(next_action)}</code></td>"
        "</tr>"
    )


def _document_snippet_html(
    document: Document,
    chunks: tuple[DocumentChunk, ...],
) -> str:
    source_text = document.inline_content or (chunks[0].raw_text if chunks else None)
    if source_text is None:
        return ""
    snippet = " ".join(source_text.split()).strip()
    if not snippet:
        return ""
    if len(snippet) > 160:
        snippet = snippet[:157].rstrip() + "..."
    return (
        '<div class="document-snippet"><strong>Snippet:</strong> '
        f"{_escape_html(snippet)}</div>"
    )


def _credibility_html_summary(
    assessment: DocumentCredibilityAssessment | None,
) -> str:
    if assessment is None:
        return ""

    parts: list[str] = []
    if assessment.summary:
        parts.append(
            f"<div><strong>Summary:</strong> {_escape_html(assessment.summary)}</div>"
        )
    if assessment.strengths:
        parts.append(_html_list_block("Strengths", assessment.strengths))
    if assessment.concerns:
        parts.append(_html_list_block("Concerns", assessment.concerns))
    if assessment.verification_checks:
        parts.append(
            _html_list_block("Verification checks", assessment.verification_checks)
        )
    if not parts:
        return ""
    return "<div class=\"credibility-detail\">" + "".join(parts) + "</div>"


def _html_list_block(label: str, items: tuple[str, ...]) -> str:
    rendered_items = "".join(f"<li>{_escape_html(item)}</li>" for item in items)
    return (
        f"<div><strong>{_escape_html(label)}:</strong>"
        f"<ul>{rendered_items}</ul></div>"
    )


def _prepare_diagnostics(outcome: DocumentPreparationOutcome) -> dict[str, object]:
    chunk_count = len(outcome.chunks)
    if chunk_count:
        summary = f"Prepared {chunk_count} chunk(s)."
        next_step = f"POST /api/documents/{outcome.document.document_id}/extract-claims"
    else:
        summary = "No chunks were prepared."
        next_step = "Provide non-empty raw_text or attach inline content before preparing."
    return {
        "chunk_count": chunk_count,
        "status": "ready" if chunk_count else "empty",
        "summary": summary,
        "next_step": next_step,
    }


def _claim_extraction_diagnostics(outcome: ClaimExtractionOutcome) -> dict[str, object]:
    claim_count = len(outcome.claims)
    chunk_count = len(outcome.chunks)
    if claim_count:
        summary = f"Extracted {claim_count} claim(s) from {chunk_count} chunk(s)."
        next_step = f"GET /api/cases/{outcome.document.case_id}/claims"
    elif not chunk_count:
        summary = "No prepared chunks were available for extraction."
        next_step = f"POST /api/documents/{outcome.document.document_id}/prepare"
    else:
        summary = "No claims were extracted from the prepared chunks."
        next_step = (
            "Inspect /api/documents/{document_id}/chunks and retry extraction with richer source text."
        ).format(document_id=outcome.document.document_id)
    return {
        "claim_count": claim_count,
        "chunk_count": chunk_count,
        "dropped_claim_items": outcome.dropped_claim_items,
        "dropped_evidence_items": outcome.dropped_evidence_items,
        "review_cautions": list(outcome.review_cautions),
        "status": "ready" if claim_count else "empty",
        "summary": summary,
        "next_step": next_step,
    }


def _escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _format_chunk_ids(chunk_ids: tuple[str, ...]) -> str:
    return ", ".join(chunk_ids) if chunk_ids else "none"


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    return _required_datetime(value, field_name="datetime")


def _required_datetime(value: object, *, field_name: str) -> datetime:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} is required.")
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid ISO-8601 datetime.") from exc


def document_from_payload(payload: dict[str, object]) -> Document:
    """Deserialize a document payload for dev/bootstrap API use."""

    document_id = str(payload.get("document_id") or "").strip()
    case_id = str(payload.get("case_id") or "").strip()
    source_type = str(payload.get("source_type") or "").strip()
    retrieved_at_raw = payload.get("retrieved_at")
    content_hash = str(payload.get("content_hash") or "").strip()
    inline_content = _optional_str(payload.get("content")) or _optional_str(payload.get("text"))
    if not document_id:
        title_hint = _optional_str(payload.get("title")) or "document"
        document_id = _slugify_identifier(title_hint, prefix="doc")
    if not case_id:
        raise ValueError("case_id is required.")
    if not source_type:
        source_type = "inline_text" if inline_content else "note"
    if retrieved_at_raw is None:
        retrieved_at_raw = datetime.now().isoformat()
    if not content_hash:
        if inline_content:
            content_hash = f"sha256:{sha256(inline_content.encode('utf-8')).hexdigest()}"
        else:
            raise ValueError("content_hash is required.")
    return Document(
        document_id=document_id,
        case_id=case_id,
        source_type=source_type,
        source_url=_optional_str(payload.get("source_url") or payload.get("source_uri")),
        publisher=_optional_str(payload.get("publisher")),
        author=_optional_str(payload.get("author")),
        title=_optional_str(payload.get("title")),
        published_at=_optional_datetime(payload.get("published_at")),
        retrieved_at=_required_datetime(retrieved_at_raw, field_name="retrieved_at"),
        content_hash=content_hash,
        language=_optional_str(payload.get("language")),
        inline_content=inline_content,
    )


def document_to_payload(document: Document) -> dict[str, object]:
    """Serialize a document for JSON API responses."""

    return {
        "document_id": document.document_id,
        "case_id": document.case_id,
        "source_type": document.source_type,
        "source_url": document.source_url,
        "publisher": document.publisher,
        "author": document.author,
        "title": document.title,
        "published_at": (
            document.published_at.isoformat() if document.published_at is not None else None
        ),
        "retrieved_at": document.retrieved_at.isoformat(),
        "content_hash": document.content_hash,
        "language": document.language,
        "has_inline_content": bool(document.inline_content),
    }



def _slugify_identifier(value: str, *, prefix: str) -> str:
    transliterated = value.replace("ł", "l").replace("Ł", "L")
    ascii_value = "".join(
        char
        for char in unicode_normalize("NFKD", transliterated)
        if not combining(char)
    ).encode("ascii", "ignore").decode("ascii")
    normalized = "".join(
        char.lower() if char.isalnum() else "-" for char in ascii_value
    ).strip("-")
    compact = "-".join(part for part in normalized.split("-") if part)
    stem = compact[:40] or prefix
    return f"{prefix}-{stem}"


__all__ = [
    "PersistenceReportAssembler",
    "SourceTraceDelivery",
    "VerificationDeliveryRequest",
    "VerificationInspection",
    "case_creation_request_from_payload",
    "case_to_payload",
    "chunk_to_payload",
    "claim_extraction_outcome_to_payload",
    "claim_from_payload",
    "claim_to_payload",
    "create_default_delivery",
    "document_preparation_outcome_to_payload",
    "document_from_payload",
    "document_to_payload",
    "evidence_link_to_payload",
    "render_case_review_html",
    "render_continuity_pack_html",
    "render_report_markdown",
    "report_entry_to_payload",
    "report_outcome_to_payload",
    "review_decision_from_payload",
    "review_decision_to_payload",
    "verification_inspection_to_payload",
    "verification_outcome_to_payload",
    "verification_to_payload",
]
