"""Thin analyst-facing delivery service over the runtime path."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from sourcetrace.application import (
    CredibilityAssessmentExecution,
    CredibilityAssessmentOutcome,
    CredibilityAssessmentRequest,
    ClaimVerificationExecution,
    ReportAssemblyExecution,
    ReportAssemblyOutcome,
    ReportAssemblyRequest,
    build_llm_credibility_assessor,
)
from sourcetrace.domain import (
    CaseReport,
    Claim,
    ClaimEvidenceLink,
    ClaimReportEntry,
    ClaimReviewDecision,
    ClaimVerification,
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
from sourcetrace.storage import create_in_memory_persistence
from sourcetrace.storage.interfaces import CorePersistence

if TYPE_CHECKING:
    from sourcetrace.llm.interfaces import CredibilityDraftGateway


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
class SourceTraceDelivery:
    """Minimal delivery surface for verification, review, and reports."""

    persistence: CorePersistence
    verification_runtime: ClaimVerificationRuntime
    report_assembly: ReportAssemblyExecution
    credibility_assessment: CredibilityAssessmentExecution | None = None

    def verify_claim(
        self,
        request: VerificationDeliveryRequest,
    ) -> ClaimVerificationRuntimeOutcome:
        """Run retrieval-backed verification and persist the resulting records."""

        return self.verification_runtime(
            ClaimVerificationRuntimeRequest(
                claim=request.claim,
                requested_k=request.requested_k,
                query_id=request.query_id,
                retrieval_method=request.retrieval_method,
                document_ids=request.document_ids,
            )
        )

    def inspect_verification(self, claim_id: str) -> VerificationInspection | None:
        """Return the persisted analyst inspection view for one verified claim."""

        claim = self.persistence.claims.get_claim(claim_id)
        verification = _get_verification(self.persistence, claim_id)
        if claim is None or verification is None:
            return None
        evidence_links = _list_evidence_links(self.persistence, claim_id)
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
        return self.credibility_assessment.assess_credibility(
            CredibilityAssessmentRequest(
                document=document,
                assessment_method=assessment_method,
            )
        )


@dataclass(frozen=True)
class PersistenceReportAssembler:
    """Report assembler that reads verified claim context from persistence."""

    persistence: CorePersistence

    def __call__(self, request: ReportAssemblyRequest) -> ReportAssemblyOutcome:
        entries = tuple(
            entry
            for decision in request.review_decisions
            if (entry := self._entry_for_decision(decision)) is not None
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

    def _entry_for_decision(
        self,
        decision: ClaimReviewDecision,
    ) -> ClaimReportEntry | None:
        if _is_excluded_from_report(decision):
            return None

        claim = self.persistence.claims.get_claim(decision.claim_id)
        verification = _get_verification(self.persistence, decision.claim_id)
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
                verification.contradicting_chunk_ids
                if verification is not None
                else ()
            ),
        )


def create_default_delivery(
    persistence: CorePersistence | None = None,
    credibility_draft: "CredibilityDraftGateway | None" = None,
    credibility_assessed_at: Callable[[], datetime] | None = None,
) -> SourceTraceDelivery:
    """Create the default in-memory analyst delivery surface."""

    persistence = persistence or create_in_memory_persistence()
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
    credibility_assessment = _build_credibility_assessment_execution(
        credibility_draft=credibility_draft,
        credibility_assessed_at=credibility_assessed_at,
    )
    return SourceTraceDelivery(
        persistence=persistence,
        verification_runtime=verification_runtime,
        report_assembly=report_assembly,
        credibility_assessment=credibility_assessment,
    )


def verification_inspection_to_payload(
    inspection: VerificationInspection,
) -> dict[str, object]:
    """Serialize a verification inspection for JSON responses."""

    return {
        "claim": claim_to_payload(inspection.claim),
        "verification": verification_to_payload(inspection.verification),
        "evidence_summary": {
            "evidence_count": inspection.evidence_count,
            "supporting_evidence_count": inspection.supporting_evidence_count,
            "contradicting_evidence_count": inspection.contradicting_evidence_count,
            "insufficient_evidence_count": inspection.insufficient_evidence_count,
            "has_review": inspection.has_review,
            "has_report_entry": inspection.has_report_entry,
        },
        "evidence_links": [
            evidence_link_to_payload(link) for link in inspection.evidence_links
        ],
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

    return {
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
        "assessed_by": assessment.assessed_by,
        "assessed_at": assessment.assessed_at.isoformat(),
        "override": assessment.override,
    }


def render_case_review_html(delivery: SourceTraceDelivery, case_id: str) -> str:
    """Render a tiny server-side analyst view for one case."""

    claims = delivery.persistence.claims.list_claims_for_case(case_id)
    rows = "\n".join(_claim_row_html(delivery, claim) for claim in claims)
    if not rows:
        rows = '<tr><td colspan="4">No claims available.</td></tr>'
    return (
        "<!doctype html>"
        "<html><head><title>SourceTrace Case Review</title></head>"
        "<body>"
        f"<h1>Case {case_id}</h1>"
        "<table>"
        "<thead><tr><th>Claim</th><th>Verdict</th><th>Review</th>"
        "<th>Evidence</th></tr></thead>"
        f"<tbody>{rows}</tbody>"
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
    verdict = verification.verdict.value if verification is not None else "unverified"
    review_status = (
        review.human_review_status.value if review is not None else "unreviewed"
    )
    evidence_count = str(len(links))
    return (
        "<tr>"
        f"<td>{_escape_html(claim.exact_text)}</td>"
        f"<td>{_escape_html(verdict)}</td>"
        f"<td>{_escape_html(review_status)}</td>"
        f"<td>{evidence_count}</td>"
        "</tr>"
    )


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


__all__ = [
    "PersistenceReportAssembler",
    "SourceTraceDelivery",
    "VerificationDeliveryRequest",
    "VerificationInspection",
    "claim_from_payload",
    "claim_to_payload",
    "create_default_delivery",
    "evidence_link_to_payload",
    "render_case_review_html",
    "render_report_markdown",
    "report_entry_to_payload",
    "report_outcome_to_payload",
    "review_decision_from_payload",
    "verification_inspection_to_payload",
    "verification_outcome_to_payload",
    "verification_to_payload",
]
