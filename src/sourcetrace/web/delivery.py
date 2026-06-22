"""Thin analyst-facing delivery service over the runtime path."""

import os
import re

from collections import Counter
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
    ResearchExecution,
    ResearchJobListOutcome,
    ResearchJobResultOutcome,
    ResearchJobStartOutcome,
    ResearchJobStartRequest,
    ResearchJobStatusOutcome,
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
    build_research_execution,
    render_continuity_pack_markdown,
)
from sourcetrace.application.interfaces import (
    ClaimVerificationExecution,
    ContinuityPackExecution,
)
from sourcetrace.application.extraction_runtime import build_llm_claim_extractor
from sourcetrace.domain import (
    Case,
    ResearchJob,
    ResearchResultArtifact,
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
from sourcetrace.pipeline.verification import _verification_controls
from sourcetrace.storage import (
    ContinuityPackPersistenceStatus,
    FileBackedCaseRepository,
    create_in_memory_persistence,
)
from sourcetrace.storage.interfaces import CorePersistence
from sourcetrace.storage.research import ResearchPersistence, create_in_memory_research_persistence

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
    review_decision: ClaimReviewDecision | None
    evidence_links: tuple[ClaimEvidenceLink, ...]
    evidence_count: int
    supporting_evidence_count: int
    contradicting_evidence_count: int
    insufficient_evidence_count: int
    has_review: bool
    has_report_entry: bool
    support_rationale: str = "unsupported_or_not_applicable"
    previously_fact_checked_matches: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True)
class ContinuityPackInspection:
    """Analyst-facing view of an assembled continuity pack."""

    title: str
    source_artifact_path: str
    sections: dict[str, tuple[str, ...]]
    decision_snapshot: tuple[str, ...]
    verification_diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceTraceDelivery:
    """Delivery surface for product resources, verification, review, and reports."""

    persistence: CorePersistence
    verification_runtime: ClaimVerificationRuntime
    report_assembly: ReportAssemblyExecution
    continuity_pack_execution: ContinuityPackExecution | None = None
    credibility_assessment: CredibilityAssessmentExecution | None = None
    claim_extraction_runtime: ClaimExtractionRuntime | None = None
    research: ResearchExecution | None = None
    research_search_backend: str = "stub"
    research_search_configured: bool = False

    def start_research_job(
        self,
        *,
        owner_id: str,
        query: str,
    ) -> ResearchJobStartOutcome | None:
        """Start a Deep Research job if the research runtime is configured."""

        if self.research is None:
            return None
        return self.research.start_job(ResearchJobStartRequest(owner_id=owner_id, query=query))

    def get_research_job_status(self, job_id: str) -> ResearchJobStatusOutcome | None:
        """Return one persisted research job status view."""

        if self.research is None:
            return None
        return self.research.get_job_status(job_id)

    def cancel_research_job(self, job_id: str) -> ResearchJob | None:
        """Cancel a running or queued research job."""

        if self.research is None:
            return None
        return self.research.cancel_job(job_id)

    def get_research_result(self, job_id: str) -> ResearchJobResultOutcome | None:
        """Return one persisted research result view."""

        if self.research is None:
            return None
        return self.research.get_job_result(job_id)

    def list_research_jobs(self, owner_id: str) -> ResearchJobListOutcome | None:
        """List persisted research jobs for one owner."""

        if self.research is None:
            return None
        return self.research.list_jobs(owner_id)

    def run_research_job(self, job_id: str) -> ResearchResultArtifact | None:
        """Run the deterministic fake research worker for one job."""

        if self.research is None:
            return None
        return self.research.run_job(job_id)

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
            review_decision=review_decision,
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
            support_rationale=_support_rationale(verification, evidence_links),
            previously_fact_checked_matches=_previously_fact_checked_matches(
                self.persistence,
                claim,
            ),
        )

    def record_review(
        self,
        review_decision: ClaimReviewDecision,
    ) -> ClaimReviewDecision | None:
        """Persist a human review decision for report assembly."""

        claim = self.persistence.claims.get_claim(review_decision.claim_id)
        if claim is None or claim.case_id != review_decision.case_id:
            return None
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
            verification_diagnostics=continuity_pack.verification_diagnostics,
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
                "research": self.research is not None,
                "research_search": self.research_search_configured,
                "research": self.research is not None,
                "research_search": self.research_search_configured,
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
                "research": _enabled(self.research),
                "research_search_backend": self.research_search_backend,
                "research_search_configured": self.research_search_configured,
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
                "research": ["start", "status", "result", "list", "cancel", "run"],
            },
            "runtime": {
                "claim_extraction": self.claim_extraction_runtime is not None,
                "credibility_assessment": self.credibility_assessment is not None,
                "research": self.research is not None,
                "research_search": self.research_search_configured,
                "research": self.research is not None,
                "research_search": self.research_search_configured,
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
                    "/api/research/start",
                    "/api/research/jobs",
                    "/api/research/status/{job_id}",
                    "/api/research/result/{job_id}",
                    "/api/research/cancel/{job_id}",
                    "/api/research/run/{job_id}",
                    "/api/continuity-packs/render-markdown",
                    "/api/reports/{case_id}",
                    "/api/reports/{case_id}.json",
                    "/api/reports/{case_id}.md",
                    "/api/reports/{case_id}.html",
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
            verification_diagnostics=tuple(
                item.strip() for item in request.verification_diagnostics if item.strip()
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
    credibility_assessment: CredibilityAssessmentExecution | None = None,
    claim_extraction: "ClaimExtractionGateway | None" = None,
    claim_normalization: "ClaimNormalizationGateway | None" = None,
    claim_extraction_runtime: ClaimExtractionRuntime | None = None,
    continuity_pack_root_dir: str | Path | None = None,
    research_persistence: ResearchPersistence | None = None,
    research: ResearchExecution | None = None,
    research_search_backend: str = "stub",
    research_search_configured: bool = False,
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
    credibility_assessment = credibility_assessment or _build_credibility_assessment_execution(
        credibility_draft=credibility_draft,
        credibility_assessed_at=credibility_assessed_at,
    )
    claim_extraction_runtime = claim_extraction_runtime or _build_claim_extraction_runtime(
        claim_extraction=claim_extraction,
        claim_normalization=claim_normalization,
    )
    research_persistence = research_persistence or create_in_memory_research_persistence()
    research = research or build_research_execution(persistence=research_persistence)
    return SourceTraceDelivery(
        persistence=persistence,
        verification_runtime=verification_runtime,
        report_assembly=report_assembly,
        continuity_pack_execution=continuity_pack_execution,
        credibility_assessment=credibility_assessment,
        claim_extraction_runtime=claim_extraction_runtime,
        research=research,
        research_search_backend=research_search_backend,
        research_search_configured=research_search_configured,
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
            "decision_support": None,
        }
    else:
        pack = continuity_pack.continuity_pack
        summary = {
            "assigned": True,
            "title": pack.title,
            "source_artifact_path": pack.source_artifact_path,
            "decision_support": _continuity_decision_support_payload(
                verification_diagnostics=pack.verification_diagnostics,
                decision_snapshot=pack.decision_snapshot,
            ),
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
        "verification": verification_to_payload(
            inspection.verification,
            inspection.review_decision,
            inspection.evidence_links,
        ),
        "evidence_links": [
            evidence_link_to_payload(link) for link in inspection.evidence_links
        ],
        "best_evidence": [
            evidence_link_to_payload(link)
            for link in _best_evidence_links(inspection.evidence_links)
        ],
        "claim_trace_summary": _claim_trace_summary_payload(inspection),
        "verification_trace_log": _verification_trace_log_payload(inspection),
        "support_rationale": inspection.support_rationale,
        "previously_fact_checked_matches": list(
            inspection.previously_fact_checked_matches
        ),
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

    decision_support = _continuity_decision_support_payload(
        verification_diagnostics=continuity_pack.verification_diagnostics,
        decision_snapshot=continuity_pack.decision_snapshot,
    )
    return {
        "title": continuity_pack.title,
        "source_artifact_path": continuity_pack.source_artifact_path,
        "confirmed": list(continuity_pack.confirmed),
        "assumptions": list(continuity_pack.assumptions),
        "to_verify": list(continuity_pack.to_verify),
        "recommended_next_test": list(continuity_pack.recommended_next_test),
        "decision_snapshot": list(continuity_pack.decision_snapshot),
        "verification_diagnostics": list(continuity_pack.verification_diagnostics),
        "decision_support": decision_support,
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
        "resource": "continuity_pack",
        "resource_id": outcome.continuity_pack.source_artifact_path,
        "continuity_pack": continuity_pack_payload,
        "next_step": "GET /continuity-packs/view?artifact_path=<path>",
    }


def _continuity_decision_support_payload(
    *,
    verification_diagnostics: tuple[str, ...],
    decision_snapshot: tuple[str, ...],
) -> dict[str, object]:
    diagnostics_empty = not verification_diagnostics
    return {
        "section_label": "Decision support",
        "verification_diagnostics_label": "Verification diagnostics",
        "decision_snapshot_label": "Decision snapshot",
        "verification_diagnostics": list(verification_diagnostics),
        "decision_snapshot": list(decision_snapshot),
        "diagnostics_status": (
            "no_verification_diagnostics" if diagnostics_empty else "ready"
        ),
        "diagnostics_empty": diagnostics_empty,
    }


def continuity_pack_inspection_to_payload(
    inspection: ContinuityPackInspection,
) -> dict[str, object]:
    """Serialize an analyst-facing continuity-pack inspection view."""

    decision_support = _continuity_decision_support_payload(
        verification_diagnostics=inspection.verification_diagnostics,
        decision_snapshot=inspection.decision_snapshot,
    )
    return {
        "title": inspection.title,
        "source_artifact_path": inspection.source_artifact_path,
        "sections": {name: list(items) for name, items in inspection.sections.items()},
        "decision_snapshot": list(inspection.decision_snapshot),
        "verification_diagnostics": list(inspection.verification_diagnostics),
        "decision_support": decision_support,
    }


def verification_outcome_to_payload(
    outcome: ClaimVerificationRuntimeOutcome,
    review_decision: ClaimReviewDecision | None = None,
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
            outcome.verification_outcome.verification,
            review_decision,
        ),
        "evidence_links": [
            evidence_link_to_payload(link) for link in outcome.evidence_links
        ],
    }


def report_outcome_to_payload(outcome: ReportAssemblyOutcome) -> dict[str, object]:
    """Serialize a case report for JSON responses."""

    verification_summary = _report_verification_summary(
        outcome.entries,
        outcome.request.review_decisions,
    )
    cost_of_failure_metrics = _report_cost_of_failure_metrics(
        outcome.entries,
        outcome.request.review_decisions,
    )
    review_queue_signals = _report_review_queue_signals(
        outcome.entries,
        outcome.request.review_decisions,
    )
    return {
        "case_report": {
            "case_id": outcome.case_report.case_id,
            "generated_claim_ids": list(outcome.case_report.generated_claim_ids),
            "report_summary": outcome.case_report.report_summary,
            "publication_summary": verification_summary["publication_summary"],
            "verification_summary": verification_summary,
            "cost_of_failure_metrics": cost_of_failure_metrics,
            "review_queue_signals": review_queue_signals,
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
    review_decisions = _review_decisions_for_case(delivery.persistence, case_id)
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
    verification_summary = _report_verification_summary(
        tuple(
            entry
            for decision in review_decisions
            if (entry := _report_entry_from_review(delivery.persistence, decision)) is not None
        ),
        review_decisions,
    )
    review_queue_signals = _report_review_queue_signals(
        tuple(
            entry
            for decision in review_decisions
            if (entry := _report_entry_from_review(delivery.persistence, decision)) is not None
        ),
        review_decisions,
    )
    verification_summary_section = _verification_summary_section_html(verification_summary)
    review_queue_section = _review_queue_summary_html(review_queue_signals)
    return (
        "<!doctype html>"
        "<html><head><title>SourceTrace Case Review</title></head>"
        "<body>"
        f"<h1>Case {case_title}</h1>"
        f"<p><strong>Case ID:</strong> {_escape_html(case_id)}</p>"
        f"<p>{case_description}</p>"
        f"<p><strong>Documents:</strong> {len(documents)} &middot; <strong>Claims:</strong> {len(claims)}</p>"
        f"{verification_summary_section}"
        f"{review_queue_section}"
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

    verification_summary = _report_verification_summary(
        outcome.entries,
        outcome.request.review_decisions,
    )
    review_queue_signals = _report_review_queue_signals(
        outcome.entries,
        outcome.request.review_decisions,
    )
    publication_summary = verification_summary["publication_summary"]
    lines = [
        f"# SourceTrace Report: {outcome.case_report.case_id}",
        "",
        outcome.case_report.report_summary or "No report entries.",
        "",
        "## Publication summary",
        "",
        f"- Allowed claims: {publication_summary['allowed_claim_count']}",
        f"- Review-required claims: {publication_summary['review_required_claim_count']}",
        f"- Blocked claims: {publication_summary['blocked_claim_count']}",
        "",
        "## Verification summary",
        "",
        f"- Evidence sufficiency: {_format_count_map_markdown(verification_summary['evidence_sufficiency'])}",
        f"- Gate counts: {_format_count_map_markdown(verification_summary['publication_gate'])}",
        f"- Gate reason: {_format_count_map_markdown(verification_summary['gate_reason'])}",
        "- Support rationale counts: "
        f"{_format_support_rationale_summary_markdown(verification_summary['support_rationale_summary'])}",
        "- Contradiction diagnostics: "
        f"{_format_count_map_markdown(verification_summary['contradiction_diagnostics'])}",
        "",
        *_review_queue_summary_markdown_lines(review_queue_signals),
        "",
    ]
    for entry in outcome.entries:
        evidence_sufficiency, publication_gate, gate_reason = _verification_controls(
            entry.final_verdict,
            entry.human_review_status,
            entry.final_verdict,
        )
        lines.extend(
            [
                f"## {entry.claim_id}",
                "",
                f"- Final verdict: {entry.final_verdict.value}",
                f"- Human review: {entry.human_review_status.value}",
                f"- Summary: {entry.summary_text}",
                f"- Evidence sufficiency: {evidence_sufficiency}",
                f"- Publication gate: {publication_gate}",
                f"- Gate reason: {gate_reason or 'none'}",
                f"- Support signals present: {'yes' if entry.supporting_chunk_ids else 'no'}",
                f"- Conflict signals present: {'yes' if entry.contradicting_chunk_ids else 'no'}",
                f"- Evidence count: {len(entry.supporting_chunk_ids) + len(entry.contradicting_chunk_ids)}",
                f"- Sufficiency summary: {_verification_sufficiency_summary(entry.final_verdict, entry.supporting_chunk_ids, entry.contradicting_chunk_ids)}",
                f"- Support rationale: {_humanize_support_rationale(_report_entry_support_rationale(entry))}",
                f"- Contradiction snippet: {_report_entry_contradiction_summary(entry)['contradiction_snippet']}",
                f"- Best evidence chunks: {_best_evidence_chunk_ids_markdown(entry.supporting_chunk_ids, entry.contradicting_chunk_ids)}",
                f"- Supporting chunks: {_format_chunk_ids(entry.supporting_chunk_ids)}",
                "- Contradicting chunks: "
                f"{_format_chunk_ids(entry.contradicting_chunk_ids)}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_report_html(outcome: ReportAssemblyOutcome) -> str:
    """Render a minimal HTML report artifact."""

    verification_summary = _report_verification_summary(
        outcome.entries,
        outcome.request.review_decisions,
    )
    review_queue_signals = _report_review_queue_signals(
        outcome.entries,
        outcome.request.review_decisions,
    )
    publication_summary = verification_summary["publication_summary"]
    report_summary = _escape_html(outcome.case_report.report_summary or "No report entries.")

    entry_sections: list[str] = []
    for entry in outcome.entries:
        evidence_sufficiency, publication_gate, gate_reason = _verification_controls(
            entry.final_verdict,
            entry.human_review_status,
            entry.final_verdict,
        )
        contradiction = _report_entry_contradiction_summary(entry)
        entry_sections.append(
            "".join(
                [
                    f"<section><h2>{_escape_html(entry.claim_id)}</h2>",
                    "<ul>",
                    f"<li><strong>Final verdict:</strong> {_escape_html(entry.final_verdict.value)}</li>",
                    f"<li><strong>Human review:</strong> {_escape_html(entry.human_review_status.value)}</li>",
                    f"<li><strong>Summary:</strong> {_escape_html(entry.summary_text)}</li>",
                    f"<li><strong>Evidence sufficiency:</strong> {_escape_html(evidence_sufficiency)}</li>",
                    f"<li><strong>Publication gate:</strong> {_escape_html(publication_gate)}</li>",
                    f"<li><strong>Gate reason:</strong> {_escape_html(gate_reason or 'none')}</li>",
                    f"<li><strong>Support signals present:</strong> {_escape_html('yes' if entry.supporting_chunk_ids else 'no')}</li>",
                    f"<li><strong>Conflict signals present:</strong> {_escape_html('yes' if entry.contradicting_chunk_ids else 'no')}</li>",
                    f"<li><strong>Evidence count:</strong> {len(entry.supporting_chunk_ids) + len(entry.contradicting_chunk_ids)}</li>",
                    f"<li><strong>Sufficiency summary:</strong> {_escape_html(_verification_sufficiency_summary(entry.final_verdict, entry.supporting_chunk_ids, entry.contradicting_chunk_ids))}</li>",
                    f"<li><strong>Support rationale:</strong> {_escape_html(_humanize_support_rationale(_report_entry_support_rationale(entry)))}</li>",
                    f"<li><strong>Contradiction snippet:</strong> {_escape_html(str(contradiction['contradiction_snippet']))}</li>",
                    f"<li><strong>Best evidence chunks:</strong> {_escape_html(_best_evidence_chunk_ids_markdown(entry.supporting_chunk_ids, entry.contradicting_chunk_ids))}</li>",
                    f"<li><strong>Supporting chunks:</strong> {_escape_html(_format_chunk_ids(entry.supporting_chunk_ids))}</li>",
                    f"<li><strong>Contradicting chunks:</strong> {_escape_html(_format_chunk_ids(entry.contradicting_chunk_ids))}</li>",
                    "</ul></section>",
                ]
            )
        )

    if not entry_sections:
        entry_sections.append("<p>No report entries.</p>")

    return (
        "<!doctype html>"
        "<html><head><title>SourceTrace Report</title></head>"
        "<body>"
        f"<h1>SourceTrace Report: {_escape_html(outcome.case_report.case_id)}</h1>"
        f"<p>{report_summary}</p>"
        "<h2>Publication summary</h2>"
        "<ul>"
        f"<li><strong>Allowed claims:</strong> {publication_summary['allowed_claim_count']}</li>"
        f"<li><strong>Review-required claims:</strong> {publication_summary['review_required_claim_count']}</li>"
        f"<li><strong>Blocked claims:</strong> {publication_summary['blocked_claim_count']}</li>"
        "</ul>"
        "<h2>Verification summary</h2>"
        "<ul>"
        f"<li><strong>Evidence sufficiency:</strong> {_escape_html(_format_count_map_markdown(verification_summary['evidence_sufficiency']))}</li>"
        f"<li><strong>Publication gate:</strong> {_escape_html(_format_count_map_markdown(verification_summary['publication_gate']))}</li>"
        f"<li><strong>Gate reason:</strong> {_escape_html(_format_count_map_markdown(verification_summary['gate_reason']))}</li>"
        f"<li><strong>Support rationale counts:</strong> {_escape_html(_format_support_rationale_summary_markdown(verification_summary['support_rationale_summary']))}</li>"
        f"<li><strong>Contradiction diagnostics:</strong> {_escape_html(_format_count_map_markdown(verification_summary['contradiction_diagnostics']))}</li>"
        "</ul>"
        f"<h2>Review queue rationale</h2>{_review_queue_html_list(review_queue_signals)}"
        f"{''.join(entry_sections)}"
        "</body></html>"
    )


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
        f"{_continuity_pack_decision_support_section_html(pack)}"
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
    review_decision: ClaimReviewDecision | None = None,
    evidence_links: tuple[ClaimEvidenceLink, ...] = (),
) -> dict[str, object]:
    """Serialize a claim verification for API responses."""

    evidence_sufficiency, publication_gate, gate_reason = _verification_controls(
        verification.verdict,
        review_status=(
            review_decision.human_review_status if review_decision is not None else None
        ),
        review_verdict=(review_decision.final_verdict if review_decision is not None else None),
    )
    support_signals_present = bool(verification.supporting_chunk_ids)
    conflict_signals_present = bool(verification.contradicting_chunk_ids)
    evidence_count = len(verification.supporting_chunk_ids) + len(
        verification.contradicting_chunk_ids
    )
    sufficiency_summary = _verification_sufficiency_summary(
        verification.verdict,
        verification.supporting_chunk_ids,
        verification.contradicting_chunk_ids,
    )
    citation_quality_flags = _citation_quality_flags(
        verdict=verification.verdict,
        supporting_chunk_ids=verification.supporting_chunk_ids,
        contradicting_chunk_ids=verification.contradicting_chunk_ids,
        evidence_links=evidence_links,
    )
    return {
        "claim_id": verification.claim_id,
        "case_id": verification.case_id,
        "verdict": verification.verdict.value,
        "supporting_chunk_ids": list(verification.supporting_chunk_ids),
        "contradicting_chunk_ids": list(verification.contradicting_chunk_ids),
        "analyst_notes": verification.analyst_notes,
        "evidence_sufficiency": evidence_sufficiency,
        "publication_gate": publication_gate,
        "gate_reason": gate_reason,
        "support_signals_present": support_signals_present,
        "conflict_signals_present": conflict_signals_present,
        "evidence_count": evidence_count,
        "sufficiency_summary": sufficiency_summary,
        "citation_quality_flags": citation_quality_flags,
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

    evidence_sufficiency, publication_gate, gate_reason = _verification_controls(
        entry.final_verdict,
        entry.human_review_status,
        entry.final_verdict,
    )
    support_signals_present = bool(entry.supporting_chunk_ids)
    conflict_signals_present = bool(entry.contradicting_chunk_ids)
    evidence_count = len(entry.supporting_chunk_ids) + len(entry.contradicting_chunk_ids)
    sufficiency_summary = _verification_sufficiency_summary(
        entry.final_verdict,
        entry.supporting_chunk_ids,
        entry.contradicting_chunk_ids,
    )
    citation_quality_flags = _citation_quality_flags(
        verdict=entry.final_verdict,
        supporting_chunk_ids=entry.supporting_chunk_ids,
        contradicting_chunk_ids=entry.contradicting_chunk_ids,
        evidence_links=(),
    )
    contradiction_summary = _report_entry_contradiction_summary(entry)
    return {
        "claim_id": entry.claim_id,
        "case_id": entry.case_id,
        "final_verdict": entry.final_verdict.value,
        "human_review_status": entry.human_review_status.value,
        "summary_text": entry.summary_text,
        "supporting_chunk_ids": list(entry.supporting_chunk_ids),
        "contradicting_chunk_ids": list(entry.contradicting_chunk_ids),
        "evidence_sufficiency": evidence_sufficiency,
        "publication_gate": publication_gate,
        "gate_reason": gate_reason,
        "support_signals_present": support_signals_present,
        "conflict_signals_present": conflict_signals_present,
        "evidence_count": evidence_count,
        "sufficiency_summary": sufficiency_summary,
        "support_rationale": _report_entry_support_rationale(entry),
        "contradiction_summary": contradiction_summary,
        "citation_quality_flags": citation_quality_flags,
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


def _verification_sufficiency_summary(
    verdict: VerificationVerdict,
    supporting_chunk_ids: tuple[str, ...],
    contradicting_chunk_ids: tuple[str, ...],
) -> str:
    evidence_count = len(supporting_chunk_ids) + len(contradicting_chunk_ids)
    if verdict is VerificationVerdict.CONTRADICT:
        return (
            f"Conflicting evidence detected across {evidence_count} retrieved chunk"
            f"{'s' if evidence_count != 1 else ''}."
        )
    if verdict is VerificationVerdict.INSUFFICIENT_EVIDENCE:
        return "No retrieved evidence established support for the claim."
    support_count = len(supporting_chunk_ids)
    return (
        f"Supporting evidence found in {support_count} retrieved chunk"
        f"{'s' if support_count != 1 else ''}."
    )


def _citation_quality_flags(
    *,
    verdict: VerificationVerdict,
    supporting_chunk_ids: tuple[str, ...],
    contradicting_chunk_ids: tuple[str, ...],
    evidence_links: tuple[ClaimEvidenceLink, ...],
) -> list[str]:
    flags: list[str] = []
    evidence_chunk_ids = tuple(link.chunk_id for link in evidence_links)
    unique_evidence_chunk_ids = {chunk_id for chunk_id in evidence_chunk_ids}
    retrieval_chunk_ids = set(supporting_chunk_ids) | set(contradicting_chunk_ids)
    if retrieval_chunk_ids and evidence_links == ():
        if supporting_chunk_ids and contradicting_chunk_ids:
            flags.append("mixed_support_and_contradiction")
        elif (
            verdict is VerificationVerdict.CONTRADICT
            and contradicting_chunk_ids
            and not supporting_chunk_ids
        ):
            flags.append("contradiction_without_support")
        return flags
    if retrieval_chunk_ids and not evidence_links:
        flags.append("missing_best_evidence")
    if evidence_links and not retrieval_chunk_ids:
        flags.append("non_retrieval_attributable")
    if evidence_links and len(unique_evidence_chunk_ids) < len(evidence_chunk_ids):
        flags.append("redundant_citation")
    if supporting_chunk_ids and contradicting_chunk_ids:
        flags.append("mixed_support_and_contradiction")
    if (
        verdict is VerificationVerdict.CONTRADICT
        and contradicting_chunk_ids
        and not supporting_chunk_ids
    ):
        flags.append("contradiction_without_support")
    if (
        verdict is VerificationVerdict.CONTRADICT
        and evidence_links
        and not contradicting_chunk_ids
    ):
        flags.append("missing_best_evidence")
    return flags


def _best_evidence_links(
    evidence_links: tuple[ClaimEvidenceLink, ...],
    *,
    limit: int = 2,
) -> tuple[ClaimEvidenceLink, ...]:
    ordered = sorted(
        evidence_links,
        key=lambda link: (link.evidence_rank, 1 if link.score is None else 0, -(link.score or 0.0)),
    )
    return tuple(ordered[:limit])


def _best_evidence_chunk_ids_markdown(
    supporting_chunk_ids: tuple[str, ...],
    contradicting_chunk_ids: tuple[str, ...],
    *,
    limit: int = 2,
) -> str:
    chunk_ids = supporting_chunk_ids[:limit] or contradicting_chunk_ids[:limit]
    if not chunk_ids:
        return "none"
    return ", ".join(chunk_ids)


def _best_evidence_html_summary(evidence_links: tuple[ClaimEvidenceLink, ...]) -> str:
    best_links = _best_evidence_links(evidence_links)
    if not best_links:
        return "none"
    parts: list[str] = []
    for link in best_links:
        snippet = " ".join(link.snippet.split()).strip() if link.snippet else ""
        if len(snippet) > 120:
            snippet = snippet[:117].rstrip() + "..."
        snippet_text = snippet or "no snippet"
        parts.append(
            f"#{link.evidence_rank} [{link.evidence_verdict.value}] {link.chunk_id}: {snippet_text}"
        )
    return " | ".join(parts)


def _claim_trace_summary_payload(inspection: VerificationInspection) -> dict[str, object]:
    verification_payload = verification_to_payload(
        inspection.verification,
        inspection.review_decision,
        inspection.evidence_links,
    )
    return {
        "final_verdict": verification_payload["verdict"],
        "evidence_sufficiency": verification_payload["evidence_sufficiency"],
        "publication_gate": verification_payload["publication_gate"],
        "gate_reason": verification_payload["gate_reason"],
        "sufficiency_summary": verification_payload["sufficiency_summary"],
        "citation_quality_flags": verification_payload["citation_quality_flags"],
        "best_evidence": [
            evidence_link_to_payload(link)
            for link in _best_evidence_links(inspection.evidence_links)
        ],
        "review_note": (
            inspection.review_decision.review_notes
            if inspection.review_decision is not None and inspection.review_decision.review_notes
            else inspection.verification.analyst_notes
        ),
    }


def _verification_trace_log_payload(inspection: VerificationInspection) -> dict[str, object]:
    verification_payload = verification_to_payload(
        inspection.verification,
        inspection.review_decision,
        inspection.evidence_links,
    )
    review_decision = inspection.review_decision
    return {
        "retrieval_trace": {
            "query_text": inspection.claim.exact_text,
            "considered_chunks": [
                {
                    "chunk_id": link.chunk_id,
                    "document_id": link.document_id,
                    "evidence_rank": link.evidence_rank,
                    "evidence_verdict": link.evidence_verdict.value,
                    "score": link.score,
                }
                for link in inspection.evidence_links
            ],
            "selected_supporting_chunks": list(inspection.verification.supporting_chunk_ids),
            "selected_contradicting_chunks": list(
                inspection.verification.contradicting_chunk_ids
            ),
        },
        "decision_trace": {
            "verdict": verification_payload["verdict"],
            "evidence_sufficiency": verification_payload["evidence_sufficiency"],
            "publication_gate": verification_payload["publication_gate"],
            "gate_reason": verification_payload["gate_reason"],
            "sufficiency_summary": verification_payload["sufficiency_summary"],
            "contradiction_trace": {
                "selected_contradicting_chunks": list(
                    inspection.verification.contradicting_chunk_ids
                ),
                "contradicting_evidence_count": inspection.contradicting_evidence_count,
                "best_contradicting_evidence": [
                    evidence_link_to_payload(link)
                    for link in _best_evidence_links(
                        tuple(
                            link
                            for link in inspection.evidence_links
                            if link.evidence_verdict is VerificationVerdict.CONTRADICT
                        )
                    )
                ],
            },
        },
        "review_trace": {
            "has_review": review_decision is not None,
            "review_status": (
                review_decision.human_review_status.value
                if review_decision is not None
                else None
            ),
            "review_verdict": (
                review_decision.final_verdict.value
                if review_decision is not None and review_decision.final_verdict is not None
                else None
            ),
            "review_notes": review_decision.review_notes if review_decision is not None else None,
        },
    }


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


def _support_rationale(
    verification: ClaimVerification,
    evidence_links: tuple[ClaimEvidenceLink, ...],
) -> str:
    if verification.verdict is VerificationVerdict.CONTRADICT:
        return "conflicting_evidence"
    if verification.verdict is not VerificationVerdict.SUPPORT:
        return "unsupported_or_not_applicable"
    supporting_links = tuple(
        link for link in evidence_links if link.evidence_verdict is VerificationVerdict.SUPPORT
    )
    if any(link.score is not None and link.score >= 1.0 for link in supporting_links):
        return "exact_lexical_match"
    if len(
        tuple(
            link
            for link in supporting_links
            if link.score is not None and 0.6 <= link.score < 1.0
        )
    ) >= 2:
        return "corroborated_partial_hits"
    return "unsupported_or_not_applicable"


def _report_entry_support_rationale(entry: ClaimReportEntry) -> str:
    if entry.final_verdict is VerificationVerdict.CONTRADICT:
        return "conflicting_evidence"
    if entry.final_verdict is not VerificationVerdict.SUPPORT:
        return "unsupported_or_not_applicable"
    if len(entry.supporting_chunk_ids) >= 2:
        return "corroborated_partial_hits"
    if len(entry.supporting_chunk_ids) == 1:
        return "exact_lexical_match"
    return "unsupported_or_not_applicable"


def _normalize_claim_match_text(text: str) -> str:
    normalized = unicode_normalize("NFKD", text)
    without_diacritics = "".join(
        character for character in normalized if not combining(character)
    )
    collapsed = " ".join(without_diacritics.casefold().split())
    return collapsed


def _claim_match_risk_flags(source_text: str, candidate_text: str) -> tuple[str, ...]:
    flags: list[str] = []
    if source_text != candidate_text and source_text.casefold() == candidate_text.casefold():
        flags.append("casefold_only_match")
    if " ".join(source_text.split()) != source_text or " ".join(candidate_text.split()) != candidate_text:
        if " ".join(source_text.casefold().split()) == " ".join(candidate_text.casefold().split()):
            flags.append("whitespace_normalized_match")
    source_without_diacritics = "".join(
        character
        for character in unicode_normalize("NFKD", source_text)
        if not combining(character)
    )
    candidate_without_diacritics = "".join(
        character
        for character in unicode_normalize("NFKD", candidate_text)
        if not combining(character)
    )
    if source_text != candidate_text and source_without_diacritics.casefold() == candidate_without_diacritics.casefold():
        if source_text.casefold() != candidate_text.casefold():
            flags.append("diacritic_stripped_match")
    return tuple(flags)


def _claim_type_signals(text: str) -> tuple[str, ...]:
    signals: list[str] = []
    normalized = text.casefold()
    if re.search(r"\b\d+(?:[.,]\d+)?%?\b", normalized) or re.search(
        r"\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b",
        normalized,
    ):
        signals.append("numeric_claim")
    if re.search(
        r"\b(19\d{2}|20\d{2}|jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|today|yesterday|tomorrow)\b",
        normalized,
    ) or re.search(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", normalized):
        signals.append("temporal_claim")
    return tuple(signals)


def _previously_fact_checked_matches(
    persistence: CorePersistence,
    claim: Claim,
) -> tuple[dict[str, object], ...]:
    normalized_target = _normalize_claim_match_text(claim.exact_text)
    if not normalized_target:
        return ()
    matches: list[dict[str, object]] = []
    for candidate in persistence.claims.list_claims_for_case(claim.case_id):
        if candidate.claim_id == claim.claim_id:
            continue
        if _normalize_claim_match_text(candidate.exact_text) != normalized_target:
            continue
        review_decision = persistence.claims.get_review_decision(candidate.claim_id)
        verification = persistence.claims.get_verification(candidate.claim_id)
        if review_decision is None and verification is None:
            continue
        final_verdict = None
        if review_decision is not None and review_decision.final_verdict is not None:
            final_verdict = review_decision.final_verdict.value
        elif verification is not None:
            final_verdict = verification.verdict.value
        matches.append(
            {
                "claim_id": candidate.claim_id,
                "case_id": candidate.case_id,
                "exact_text": candidate.exact_text,
                "human_review_status": (
                    review_decision.human_review_status.value
                    if review_decision is not None
                    else None
                ),
                "final_verdict": final_verdict,
                "normalization_risk_flags": list(
                    _claim_match_risk_flags(claim.exact_text, candidate.exact_text)
                ),
                "claim_type_signals": list(_claim_type_signals(candidate.exact_text)),
            }
        )
    return tuple(sorted(matches, key=lambda item: str(item["claim_id"])))


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


def _report_publication_summary(
    entries: tuple[ClaimReportEntry, ...],
    review_decisions: tuple[ClaimReviewDecision, ...] = (),
) -> dict[str, int]:
    summary = _report_verification_summary(entries, review_decisions)
    publication_summary = summary["publication_summary"]
    return {
        "allowed_claim_count": int(publication_summary["allowed_claim_count"]),
        "review_required_claim_count": int(
            publication_summary["review_required_claim_count"]
        ),
        "blocked_claim_count": int(publication_summary["blocked_claim_count"]),
    }


def _report_verification_summary(
    entries: tuple[ClaimReportEntry, ...],
    review_decisions: tuple[ClaimReviewDecision, ...] = (),
) -> dict[str, dict[str, int]]:
    allowed_claim_count = 0
    review_required_claim_count = 0
    blocked_claim_count = 0
    evidence_sufficiency_counts: Counter[str] = Counter()
    publication_gate_counts: Counter[str] = Counter()
    gate_reason_counts: Counter[str] = Counter()
    support_rationale_counts: Counter[str] = Counter()
    contradicted_claim_count = 0
    contradicting_chunk_count = 0
    claims_with_mixed_support_and_contradiction_count = 0
    excluded_claim_ids = {
        decision.claim_id
        for decision in review_decisions
        if _is_excluded_from_report(decision)
    }
    blocked_claim_count += len(excluded_claim_ids)
    for entry in entries:
        if entry.claim_id in excluded_claim_ids:
            continue
        evidence_sufficiency, publication_gate, gate_reason = _verification_controls(
            entry.final_verdict,
            entry.human_review_status,
            entry.final_verdict,
        )
        evidence_sufficiency_counts[evidence_sufficiency] += 1
        publication_gate_counts[publication_gate] += 1
        gate_reason_counts[gate_reason or "none"] += 1
        support_rationale_counts[_report_entry_support_rationale(entry)] += 1
        contradicting_chunk_count += len(entry.contradicting_chunk_ids)
        if entry.final_verdict is VerificationVerdict.CONTRADICT:
            contradicted_claim_count += 1
        if entry.supporting_chunk_ids and entry.contradicting_chunk_ids:
            claims_with_mixed_support_and_contradiction_count += 1
        if publication_gate == "allowed":
            allowed_claim_count += 1
        elif publication_gate == "blocked":
            blocked_claim_count += 1
        else:
            review_required_claim_count += 1
    if excluded_claim_ids:
        publication_gate_counts["blocked"] += len(excluded_claim_ids)
        gate_reason_counts["human_review_excluded"] += len(excluded_claim_ids)
    return {
        "publication_summary": {
            "allowed_claim_count": allowed_claim_count,
            "review_required_claim_count": review_required_claim_count,
            "blocked_claim_count": blocked_claim_count,
        },
        "support_rationale_summary": {
            "exact_lexical_match_count": int(
                support_rationale_counts["exact_lexical_match"]
            ),
            "corroborated_partial_hits_count": int(
                support_rationale_counts["corroborated_partial_hits"]
            ),
            "conflicting_evidence_count": int(
                support_rationale_counts["conflicting_evidence"]
            ),
            "unsupported_or_not_applicable_count": int(
                support_rationale_counts["unsupported_or_not_applicable"]
            ),
        },
        "contradiction_diagnostics": {
            "contradicted_claim_count": contradicted_claim_count,
            "contradicting_chunk_count": contradicting_chunk_count,
            "claims_with_mixed_support_and_contradiction_count": (
                claims_with_mixed_support_and_contradiction_count
            ),
        },
        "evidence_sufficiency": dict(sorted(evidence_sufficiency_counts.items())),
        "publication_gate": dict(sorted(publication_gate_counts.items())),
        "gate_reason": dict(sorted(gate_reason_counts.items())),
    }


def _report_cost_of_failure_metrics(
    entries: tuple[ClaimReportEntry, ...],
    review_decisions: tuple[ClaimReviewDecision, ...] = (),
) -> dict[str, int | float]:
    verification_summary = _report_verification_summary(entries, review_decisions)
    publication_summary = verification_summary["publication_summary"]
    claim_count = len(entries)
    evidence_count = sum(len(entry.supporting_chunk_ids) + len(entry.contradicting_chunk_ids) for entry in entries)
    claims_review_required = int(publication_summary["review_required_claim_count"])
    claims_insufficient = int(
        verification_summary["evidence_sufficiency"].get("insufficient", 0)
    )
    blocked_claim_count = int(publication_summary["blocked_claim_count"])
    publication_block_rate = (
        blocked_claim_count / claim_count if claim_count else 0.0
    )
    return {
        "claim_count": claim_count,
        "evidence_count": evidence_count,
        "claims_review_required": claims_review_required,
        "claims_insufficient": claims_insufficient,
        "publication_block_rate": publication_block_rate,
    }


def _report_review_queue_signals(
    entries: tuple[ClaimReportEntry, ...],
    review_decisions: tuple[ClaimReviewDecision, ...] = (),
) -> dict[str, object]:
    excluded_claim_ids = {
        decision.claim_id
        for decision in review_decisions
        if _is_excluded_from_report(decision)
    }
    reason_buckets: Counter[str] = Counter()
    priority_buckets: Counter[str] = Counter()
    rationale_class_summary: Counter[str] = Counter()
    priority_rationale: list[dict[str, object]] = []
    for entry in entries:
        if entry.claim_id in excluded_claim_ids:
            continue
        _, publication_gate, gate_reason = _verification_controls(
            entry.final_verdict,
            entry.human_review_status,
            entry.final_verdict,
        )
        if publication_gate != "review_required":
            continue
        reason_key = gate_reason or "unspecified"
        reason_buckets[reason_key] += 1
        citation_quality_flags = _citation_quality_flags(
            verdict=entry.final_verdict,
            supporting_chunk_ids=entry.supporting_chunk_ids,
            contradicting_chunk_ids=entry.contradicting_chunk_ids,
            evidence_links=(),
        )
        support_rationale = _report_entry_support_rationale(entry)
        rationale_flags: list[str] = []
        if reason_key == "conflicting_evidence":
            rationale_flags.append("gate_reason_conflicting_evidence")
        if "mixed_support_and_contradiction" in citation_quality_flags:
            rationale_flags.append("mixed_support_and_contradiction")
        priority = "high" if rationale_flags else "normal"
        if reason_key == "conflicting_evidence":
            rationale_class_summary["conflict_driven"] += 1
        elif "mixed_support_and_contradiction" in citation_quality_flags:
            rationale_class_summary["mixed_support_conflict"] += 1
        elif reason_key == "no_verified_support":
            rationale_class_summary["no_support_driven"] += 1
        else:
            rationale_class_summary["other_review_required"] += 1
        priority_buckets[priority] += 1
        priority_rationale.append(
            {
                "claim_id": entry.claim_id,
                "priority": priority,
                "gate_reason": reason_key,
                "support_rationale": support_rationale,
                "citation_quality_flags": citation_quality_flags,
                "rationale_flags": rationale_flags,
            }
        )
    return {
        "review_required_claim_count": sum(reason_buckets.values()),
        "reason_buckets": dict(sorted(reason_buckets.items())),
        "priority_buckets": dict(sorted(priority_buckets.items())),
        "rationale_class_summary": dict(sorted(rationale_class_summary.items())),
        "priority_rationale": priority_rationale,
    }


def _format_count_map_markdown(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{name}={count}" for name, count in counts.items())


def _humanize_support_rationale(rationale: str) -> str:
    return rationale.replace("_", " ")


def _humanize_review_queue_priority(priority: str) -> str:
    return priority.replace("_", " ")


def _humanize_review_queue_gate_reason(reason: str) -> str:
    return reason.replace("_", " ")


def _humanize_review_queue_flags(flags: object) -> str:
    if not isinstance(flags, list) or not flags:
        return "none"
    return ", ".join(str(flag).replace("_", " ") for flag in flags)


def _humanize_review_queue_rationale_class_summary(summary: dict[str, int]) -> dict[str, int]:
    return {key.replace("_", " "): value for key, value in summary.items()}


def _format_support_rationale_summary_markdown(summary: dict[str, int]) -> str:
    parts = []
    for key in (
        "exact_lexical_match_count",
        "corroborated_partial_hits_count",
        "conflicting_evidence_count",
        "unsupported_or_not_applicable_count",
    ):
        parts.append(
            f"{_humanize_support_rationale(key.removesuffix('_count'))}={summary.get(key, 0)}"
        )
    return ", ".join(parts)


def _review_queue_priority_buckets(review_queue_signals: dict[str, object]) -> dict[str, int]:
    buckets = review_queue_signals.get("priority_buckets")
    return buckets if isinstance(buckets, dict) else {}


def _review_queue_rationale_class_summary(review_queue_signals: dict[str, object]) -> dict[str, int]:
    summary = review_queue_signals.get("rationale_class_summary")
    return summary if isinstance(summary, dict) else {}


def _review_queue_priority_rationale_markdown_lines(
    review_queue_signals: dict[str, object],
) -> list[str]:
    items = review_queue_signals.get("priority_rationale")
    if not isinstance(items, list):
        return []
    lines: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        citation_flags = item.get("citation_quality_flags")
        rationale_flags = item.get("rationale_flags")
        lines.append(
            "- Claim "
            f"{item.get('claim_id', 'unknown')}: priority={_humanize_review_queue_priority(str(item.get('priority', 'unknown')))}, "
            f"gate reason={_humanize_review_queue_gate_reason(str(item.get('gate_reason', 'unknown')))}, "
            f"support rationale={_humanize_support_rationale(str(item.get('support_rationale', 'unknown')))}, "
            f"citation flags={_humanize_review_queue_flags(citation_flags)}, "
            f"rationale flags={_humanize_review_queue_flags(rationale_flags)}"
        )
    return lines


def _review_queue_summary_markdown_lines(
    review_queue_signals: dict[str, object],
) -> list[str]:
    review_required_count = review_queue_signals.get("review_required_claim_count")
    review_required_claim_count = (
        review_required_count if isinstance(review_required_count, int) else 0
    )
    if review_required_claim_count == 0:
        return [
            "## Review queue rationale",
            "",
            "- Review-required claims: 0",
            "- Priority buckets: none",
            "- Rationale classes: none",
            "- Queue status: no review-required claims",
        ]
    return [
        "## Review queue rationale",
        "",
        f"- Review-required claims: {review_required_claim_count}",
        f"- Priority buckets: {_format_count_map_markdown(_review_queue_priority_buckets(review_queue_signals))}",
        "- Rationale classes: "
        f"{_format_count_map_markdown(_humanize_review_queue_rationale_class_summary(_review_queue_rationale_class_summary(review_queue_signals)))}",
        *_review_queue_priority_rationale_markdown_lines(review_queue_signals),
    ]


def _review_queue_priority_rationale_html(review_queue_signals: dict[str, object]) -> str:
    items = review_queue_signals.get("priority_rationale")
    if not isinstance(items, list) or not items:
        return "<p><strong>Priority rationale:</strong> none</p>"
    rendered: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        citation_flags = item.get("citation_quality_flags")
        rationale_flags = item.get("rationale_flags")
        rendered.append(
            "<li>"
            f"<strong>{_escape_html(str(item.get('claim_id', 'unknown')))}</strong>: "
            f"priority={_escape_html(_humanize_review_queue_priority(str(item.get('priority', 'unknown'))))}, "
            f"gate reason={_escape_html(_humanize_review_queue_gate_reason(str(item.get('gate_reason', 'unknown'))))}, "
            f"support rationale={_escape_html(_humanize_support_rationale(str(item.get('support_rationale', 'unknown'))))}, "
            f"citation flags={_escape_html(_humanize_review_queue_flags(citation_flags))}, "
            f"rationale flags={_escape_html(_humanize_review_queue_flags(rationale_flags))}"
            "</li>"
        )
    return "<p><strong>Priority rationale:</strong></p><ul>" + "".join(rendered) + "</ul>"


def _review_queue_summary_html(review_queue_signals: dict[str, object]) -> str:
    items = review_queue_signals.get("priority_rationale")
    review_required_count = review_queue_signals.get("review_required_claim_count")
    review_required_claim_count = (
        review_required_count if isinstance(review_required_count, int) else 0
    )
    if review_required_claim_count == 0 or not isinstance(items, list) or not items:
        return (
            "<p><strong>Priority rationale classes:</strong> none</p>"
            "<p><strong>Priority rationale:</strong> none</p>"
            "<p><strong>Queue status:</strong> no review-required claims</p>"
        )
    rationale_classes = _format_count_map_markdown(
        _humanize_review_queue_rationale_class_summary(
            _review_queue_rationale_class_summary(review_queue_signals)
        )
    )
    return (
        f"<p><strong>Priority rationale classes:</strong> {_escape_html(rationale_classes)}</p>"
        f"{_review_queue_priority_rationale_html(review_queue_signals)}"
    )


def _review_queue_html_list(review_queue_signals: dict[str, object]) -> str:
    review_required_count = review_queue_signals.get("review_required_claim_count")
    review_required_claim_count = (
        review_required_count if isinstance(review_required_count, int) else 0
    )
    if review_required_claim_count == 0:
        return (
            "<ul>"
            "<li><strong>Review-required claims:</strong> 0</li>"
            "<li><strong>Priority buckets:</strong> none</li>"
            "<li><strong>Rationale classes:</strong> none</li>"
            "<li><strong>Queue status:</strong> no review-required claims</li>"
            "</ul>"
        )
    return (
        "<ul>"
        f"<li><strong>Review-required claims:</strong> {review_required_claim_count}</li>"
        f"<li><strong>Priority buckets:</strong> {_escape_html(_format_count_map_markdown(_review_queue_priority_buckets(review_queue_signals)))}</li>"
        f"<li><strong>Rationale classes:</strong> {_escape_html(_format_count_map_markdown(_humanize_review_queue_rationale_class_summary(_review_queue_rationale_class_summary(review_queue_signals))))}</li>"
        "</ul>"
        f"{_review_queue_priority_rationale_html(review_queue_signals)}"
    )


def _verification_summary_section_html(
    verification_summary: dict[str, dict[str, int]],
) -> str:
    publication_summary = verification_summary["publication_summary"]
    return (
        "<h2>Verification summary</h2>"
        f"<p><strong>Evidence sufficiency:</strong> {_escape_html(_format_count_map_markdown(verification_summary['evidence_sufficiency']))}</p>"
        f"<p><strong>Publication gate:</strong> {_escape_html(_format_count_map_markdown(verification_summary['publication_gate']))}</p>"
        f"<p><strong>Gate reason:</strong> {_escape_html(_format_count_map_markdown(verification_summary['gate_reason']))}</p>"
        f"<p><strong>Support rationale counts:</strong> {_escape_html(_format_support_rationale_summary_markdown(verification_summary['support_rationale_summary']))}</p>"
        f"<p><strong>Contradiction diagnostics:</strong> {_escape_html(_format_count_map_markdown(verification_summary['contradiction_diagnostics']))}</p>"
        f"<p><strong>Allowed claims:</strong> {publication_summary['allowed_claim_count']} &middot; "
        f"<strong>Review-required claims:</strong> {publication_summary['review_required_claim_count']} &middot; "
        f"<strong>Blocked claims:</strong> {publication_summary['blocked_claim_count']}</p>"
    )


def _claim_row_html(delivery: SourceTraceDelivery, claim: Claim) -> str:
    verification = _get_verification(delivery.persistence, claim.claim_id)
    review = _get_review_decision(delivery.persistence, claim.claim_id)
    links = _list_evidence_links(delivery.persistence, claim.claim_id)
    verdict = _display_verdict(claim, verification)
    verdict_enum = (
        verification.verdict if verification is not None else claim.system_verdict
    )
    evidence_sufficiency, publication_gate, gate_reason = _verification_controls(
        verdict_enum,
        review.human_review_status if review is not None else None,
        review.final_verdict if review is not None else None,
    )
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
    verification_supporting_chunk_ids = (
        verification.supporting_chunk_ids if verification is not None else ()
    )
    verification_contradicting_chunk_ids = (
        verification.contradicting_chunk_ids if verification is not None else ()
    )
    citation_quality_flags = (
        _citation_quality_flags(
            verdict=verification.verdict,
            supporting_chunk_ids=verification_supporting_chunk_ids,
            contradicting_chunk_ids=verification_contradicting_chunk_ids,
            evidence_links=links,
        )
        if verification is not None
        else []
    )
    contradiction_snippet = (
        _report_entry_contradiction_summary(
            ClaimReportEntry(
                claim_id=claim.claim_id,
                case_id=claim.case_id,
                final_verdict=verdict_enum,
                human_review_status=(
                    review.human_review_status
                    if review is not None
                    else HumanReviewStatus.UNREVIEWED
                ),
                summary_text="",
                supporting_chunk_ids=verification_supporting_chunk_ids,
                contradicting_chunk_ids=verification_contradicting_chunk_ids,
            )
        )["contradiction_snippet"]
        if verification is not None
        else "No contradicting chunks selected."
    )
    claim_detail_lines = [
        _escape_html(claim.exact_text),
        f"Evidence sufficiency: {_escape_html(evidence_sufficiency)}",
        f"Publication gate: {_escape_html(publication_gate)}",
        f"Gate reason: {_escape_html(gate_reason or 'none')}",
        f"Support signals present: {'yes' if verification_supporting_chunk_ids else 'no'}",
        f"Conflict signals present: {'yes' if verification_contradicting_chunk_ids else 'no'}",
        "Evidence count: "
        f"{len(verification_supporting_chunk_ids) + len(verification_contradicting_chunk_ids)}",
        "Sufficiency summary: "
        f"{_escape_html(_verification_sufficiency_summary(verdict_enum, verification_supporting_chunk_ids, verification_contradicting_chunk_ids))}",
        "Support rationale: "
        f"{_escape_html(_humanize_support_rationale(_support_rationale(verification, links) if verification is not None else 'unsupported_or_not_applicable'))}",
        f"Contradiction snippet: {_escape_html(str(contradiction_snippet))}",
        f"Citation quality flags: {_escape_html(', '.join(citation_quality_flags) if citation_quality_flags else 'none')}",
        f"Best evidence: {_escape_html(_best_evidence_html_summary(links))}",
    ]
    return (
        "<tr>"
        f"<td>{'<br>'.join(claim_detail_lines)}<br><small>{' · '.join(claim_links)}</small></td>"
        f"<td>{_escape_html(verdict)}</td>"
        f"<td>{_escape_html(review_status)}</td>"
        f"<td>{evidence_count}</td>"
        "</tr>"
    )


def _continuity_pack_list_html(items: tuple[str, ...]) -> str:
    if not items:
        return "<ul><li>None.</li></ul>"
    return "<ul>" + "".join(f"<li>{_escape_html(item)}</li>" for item in items) + "</ul>"


def _continuity_pack_verification_diagnostics_html(items: tuple[str, ...]) -> str:
    if not items:
        return (
            "<p><strong>Diagnostics status:</strong> no verification diagnostics</p>"
            "<p><strong>Diagnostics:</strong> none</p>"
        )
    return "<ul>" + "".join(
        f"<li>{_escape_html(_humanize_continuity_verification_diagnostic_text(item))}</li>"
        for item in items
    ) + "</ul>"


def _continuity_pack_decision_support_section_html(pack: ContinuityPack) -> str:
    return (
        "<h2>Decision support</h2>"
        "<p><strong>Verification diagnostics:</strong></p>"
        f"{_continuity_pack_verification_diagnostics_html(pack.verification_diagnostics)}"
        "<p><strong>Decision snapshot:</strong></p>"
        f"{_continuity_pack_list_html(pack.decision_snapshot)}"
    )


def _continuity_pack_verification_diagnostics_section_html(items: tuple[str, ...]) -> str:
    return (
        "<h2>Verification diagnostics</h2>"
        f"{_continuity_pack_verification_diagnostics_html(items)}"
    )


def _humanize_continuity_verification_diagnostic_text(item: str) -> str:
    text = item.strip()
    if not text:
        return text
    if ":" not in text:
        return text.replace("_", " ")
    label, value = text.split(":", 1)
    humanized_label = label.strip().replace("_", " ").capitalize()
    humanized_value = value.strip().replace("_", " ")
    return f"{humanized_label}: {humanized_value}" if humanized_value else humanized_label


def _suggested_continuity_pack_artifacts_html(
    *,
    replace: bool,
) -> str:
    suggestions = _discover_continuity_pack_artifact_paths()
    if not suggestions:
        return ""
    action_label = "Replace with this continuity pack" if replace else "Assign this continuity pack"
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
    docs_dir = Path(__file__).resolve().parents[3] / "docs"
    if not docs_dir.exists():
        return ()
    suggestions: list[str] = []
    for path in sorted(docs_dir.glob("*continuity-pack*.md")):
        relative_path = path.relative_to(Path(__file__).resolve().parents[3]).as_posix()
        if "usage-note" in path.name or "broken-" in path.name:
            continue
        suggestions.append(relative_path)
    return tuple(suggestions)


def _case_continuity_pack_decision_support_html(pack: ContinuityPack) -> str:
    return (
        "<h3>Decision support</h3>"
        "<p><strong>Verification diagnostics:</strong></p>"
        f"{_continuity_pack_verification_diagnostics_html(pack.verification_diagnostics)}"
        "<p><strong>Decision snapshot:</strong></p>"
        f"{_continuity_pack_list_html(pack.decision_snapshot)}"
    )


def _case_continuity_pack_section_html(
    continuity_pack: ContinuityPackOutcome | None,
    *,
    latest_previous_continuity_pack: ContinuityPackOutcome | None = None,
) -> str:
    previous_pack = (
        latest_previous_continuity_pack.continuity_pack
        if latest_previous_continuity_pack is not None
        else None
    )
    if continuity_pack is None:
        suggested_artifacts_html = _suggested_continuity_pack_artifacts_html(replace=False)
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
                "<p><strong>Status:</strong> No active continuity pack is assigned.</p>"
                f"<p><strong>Title:</strong> {_escape_html(previous_pack.title)}</p>"
                f"<p><strong>Source artifact:</strong> <code>{_escape_html(previous_pack.source_artifact_path)}</code></p>"
                f"<p><a href=\"{_escape_html(previous_view_href)}\">View previous continuity pack</a>"
                " &middot; "
                f"<a href=\"{_escape_html(previous_assign_href)}\">Reassign this continuity pack</a></p>"
                f"{_case_continuity_pack_decision_support_html(previous_pack)}"
            )
        return (
            "<h2>Continuity pack</h2>"
            "<p><strong>Status:</strong> No active continuity pack is assigned.</p>"
            "<p><strong>Next step:</strong> Assign a continuity pack from "
            "<code>docs/...continuity-pack...</code> via "
            "<code>POST /api/cases/{case_id}/continuity-pack</code>.</p>"
            f"{latest_previous_html}"
            f"{suggested_artifacts_html}"
        )
    pack = continuity_pack.continuity_pack
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
            f"<p><a href=\"{_escape_html(previous_view_href)}\">View previous continuity pack</a>"
            " &middot; "
            f"<a href=\"{_escape_html(previous_assign_href)}\">Reassign this continuity pack</a></p>"
            f"{_case_continuity_pack_decision_support_html(previous_pack)}"
        )
    return (
        "<h2>Continuity pack</h2>"
        f"<p><strong>Title:</strong> {_escape_html(pack.title)}</p>"
        f"<p><strong>Source artifact:</strong> <code>{_escape_html(pack.source_artifact_path)}</code></p>"
        "<p><strong>Replace note:</strong> Assigning a new continuity pack replaces the current active continuity pack for this case.</p>"
        f"<p><a href=\"{_escape_html(view_href)}\">View continuity pack</a>"
        " &middot; "
        f"<a href=\"{_escape_html(render_href)}\">Render continuity pack markdown</a>"
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
        f"{_case_continuity_pack_decision_support_html(pack)}"
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


def _report_entry_contradiction_summary(entry: ClaimReportEntry) -> dict[str, object]:
    contradicting_chunks_preview = list(entry.contradicting_chunk_ids[:2])
    has_contradiction = bool(entry.contradicting_chunk_ids)
    if has_contradiction:
        contradiction_snippet = (
            "Conflicting evidence flagged in chunks: "
            f"{_format_chunk_ids(entry.contradicting_chunk_ids[:2])}."
        )
    else:
        contradiction_snippet = "No contradicting chunks selected."
    return {
        "has_contradiction": has_contradiction,
        "contradicting_chunk_count": len(entry.contradicting_chunk_ids),
        "contradicting_chunks_preview": contradicting_chunks_preview,
        "contradiction_snippet": contradiction_snippet,
    }


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
