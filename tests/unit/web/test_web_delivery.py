import json
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from io import BytesIO
from typing import cast
from wsgiref.util import setup_testing_defaults

import pytest

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
)
from sourcetrace.domain.types import (
    AnalystDisposition,
    HumanReviewStatus,
    VerificationVerdict,
)
from sourcetrace.llm.models import LlmGenerationResult, LlmStructuredGenerationResult
from sourcetrace.storage import create_in_memory_persistence
from sourcetrace.application.reporting import ReportAssemblyOutcome, ReportAssemblyRequest
from sourcetrace.web import (
    PersistenceReportAssembler,
    SourceTraceDelivery,
    SourceTraceWSGIApp,
    VerificationDeliveryRequest,
    create_default_delivery,
    create_wsgi_app,
    create_wsgi_server,
    run_local_server,
    verification_inspection_to_payload,
    verification_to_payload,
    render_report_markdown,
    report_outcome_to_payload,
)
from sourcetrace.web.api import SourceTraceWSGIApp as ModuleSourceTraceWSGIApp
from sourcetrace.web.api import create_wsgi_app as module_create_wsgi_app
from sourcetrace.web.api import create_wsgi_server as module_create_wsgi_server
from sourcetrace.web.api import run_local_server as module_run_local_server
from sourcetrace.web.delivery import (
    PersistenceReportAssembler as ModulePersistenceReportAssembler,
    VerificationInspection,
    report_entry_to_payload,
)
from sourcetrace.web.delivery import SourceTraceDelivery as ModuleSourceTraceDelivery
from sourcetrace.web.delivery import (
    VerificationDeliveryRequest as ModuleVerificationDeliveryRequest,
)
from sourcetrace.web.delivery import create_default_delivery as module_create_default_delivery
from sourcetrace.web.delivery import render_case_review_html


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
    case_report = payload["case_report"]
    assert case_report["generated_claim_ids"] == ["claim-1"]
    assert case_report["entries"][0]["supporting_chunk_ids"] == ["chunk-1"]
    assert case_report["entries"][0]["evidence_sufficiency"] == "supported"
    assert case_report["entries"][0]["publication_gate"] == "allowed"
    assert case_report["entries"][0]["gate_reason"] is None
    assert case_report["entries"][0]["support_signals_present"] is True
    assert case_report["entries"][0]["conflict_signals_present"] is False
    assert case_report["entries"][0]["evidence_count"] == 1
    assert case_report["entries"][0]["support_rationale"] == "exact_lexical_match"
    assert (
        case_report["entries"][0]["sufficiency_summary"]
        == "Supporting evidence found in 1 retrieved chunk."
    )
    assert case_report["entries"][0]["citation_quality_flags"] == []
    assert case_report["publication_summary"] == {
        "allowed_claim_count": 1,
        "review_required_claim_count": 0,
        "blocked_claim_count": 0,
    }
    assert payload["case_report"]["verification_summary"] == {
        "publication_summary": {
            "allowed_claim_count": 1,
            "review_required_claim_count": 0,
            "blocked_claim_count": 0,
        },
        "support_rationale_summary": {
            "exact_lexical_match_count": 1,
            "corroborated_partial_hits_count": 0,
            "conflicting_evidence_count": 0,
            "unsupported_or_not_applicable_count": 0,
        },
        "contradiction_diagnostics": {
            "contradicted_claim_count": 0,
            "contradicting_chunk_count": 0,
            "claims_with_mixed_support_and_contradiction_count": 0,
        },
        "evidence_sufficiency": {"supported": 1},
        "publication_gate": {"allowed": 1},
        "gate_reason": {"none": 1},
    }
    cost_of_failure_metrics = payload["case_report"]["cost_of_failure_metrics"]
    assert cost_of_failure_metrics == {
        "claim_count": 1,
        "evidence_count": 1,
        "claims_review_required": 0,
        "claims_insufficient": 0,
        "publication_block_rate": 0.0,
    }
    assert "## Verification summary" in markdown
    assert "- Evidence sufficiency: supported=1" in markdown
    assert "- Gate counts: allowed=1" in markdown
    assert "- Gate reason: none=1" in markdown
    assert "- Support rationale counts: exact lexical match=1, corroborated partial hits=0, conflicting evidence=0, unsupported or not applicable=0" in markdown
    assert "- Contradiction diagnostics: contradicted_claim_count=0, contradicting_chunk_count=0, claims_with_mixed_support_and_contradiction_count=0" in markdown
    assert "## Review queue rationale" in markdown
    assert "- Review-required claims: 0" in markdown
    assert "- Priority buckets: none" in markdown
    assert "- Rationale classes: none" in markdown
    assert "- Queue status: no review-required claims" in markdown
    assert "Analyst confirmed the bridge reopened." in markdown
    assert "- Final verdict: support" in markdown
    assert "- Evidence sufficiency: supported" in markdown
    assert "- Publication gate: allowed" in markdown
    assert "- Support signals present: yes" in markdown
    assert "- Conflict signals present: no" in markdown
    assert "- Evidence count: 1" in markdown
    assert "- Sufficiency summary: Supporting evidence found in 1 retrieved chunk." in markdown
    assert "- Support rationale: exact lexical match" in markdown
    assert "- Best evidence chunks: chunk-1" in markdown


def test_report_payload_counts_excluded_review_as_blocked() -> None:
    delivery = _seeded_delivery()
    delivery.verify_claim(VerificationDeliveryRequest(claim=_claim(), requested_k=2))
    delivery.record_review(
        ClaimReviewDecision(
            claim_id="claim-1",
            case_id="case-1",
            human_review_status=HumanReviewStatus.EXCLUDED,
            analyst_disposition=AnalystDisposition.EXCLUDE_FROM_REPORT,
            final_verdict=VerificationVerdict.SUPPORT,
            review_notes="Excluded from publication.",
        )
    )

    outcome = delivery.assemble_case_report("case-1")
    payload = report_outcome_to_payload(outcome)
    markdown = render_report_markdown(outcome)

    assert payload["case_report"]["entries"] == []
    assert payload["case_report"]["publication_summary"] == {
        "allowed_claim_count": 0,
        "review_required_claim_count": 0,
        "blocked_claim_count": 1,
    }
    assert payload["case_report"]["verification_summary"] == {
        "publication_summary": {
            "allowed_claim_count": 0,
            "review_required_claim_count": 0,
            "blocked_claim_count": 1,
        },
        "support_rationale_summary": {
            "exact_lexical_match_count": 0,
            "corroborated_partial_hits_count": 0,
            "conflicting_evidence_count": 0,
            "unsupported_or_not_applicable_count": 0,
        },
        "contradiction_diagnostics": {
            "contradicted_claim_count": 0,
            "contradicting_chunk_count": 0,
            "claims_with_mixed_support_and_contradiction_count": 0,
        },
        "evidence_sufficiency": {},
        "publication_gate": {"blocked": 1},
        "gate_reason": {"human_review_excluded": 1},
    }
    assert "## Publication summary" in markdown
    assert "## Verification summary" in markdown
    assert "- Gate reason: human_review_excluded=1" in markdown
    assert "- Allowed claims: 0" in markdown
    assert "- Review-required claims: 0" in markdown
    assert "- Blocked claims: 1" in markdown


def test_report_entry_payload_flags_corroborated_partial_support_rationale() -> None:
    payload = report_entry_to_payload(
        ClaimReportEntry(
            claim_id="claim-corroborated",
            case_id="case-1",
            final_verdict=VerificationVerdict.SUPPORT,
            human_review_status=HumanReviewStatus.UNREVIEWED,
            summary_text="Two corroborating partial hits support the claim.",
            supporting_chunk_ids=("chunk-a", "chunk-b"),
            contradicting_chunk_ids=(),
        )
    )

    assert payload["support_rationale"] == "corroborated_partial_hits"
    assert payload["evidence_count"] == 2
    assert payload["publication_gate"] == "allowed"


def test_report_entry_payload_flags_conflicting_evidence_rationale() -> None:
    payload = report_entry_to_payload(
        ClaimReportEntry(
            claim_id="claim-conflict",
            case_id="case-1",
            final_verdict=VerificationVerdict.CONTRADICT,
            human_review_status=HumanReviewStatus.UNREVIEWED,
            summary_text="Conflicting evidence needs analyst review.",
            supporting_chunk_ids=("chunk-support",),
            contradicting_chunk_ids=("chunk-contradict",),
        )
    )

    assert payload["support_rationale"] == "conflicting_evidence"
    assert payload["citation_quality_flags"] == ["mixed_support_and_contradiction"]
    assert payload["contradiction_summary"] == {
        "has_contradiction": True,
        "contradicting_chunk_count": 1,
        "contradicting_chunks_preview": ["chunk-contradict"],
        "contradiction_snippet": "Conflicting evidence flagged in chunks: chunk-contradict.",
    }
    assert payload["publication_gate"] == "review_required"
    assert payload["evidence_count"] == 2


def test_report_entry_payload_flags_contradiction_without_support() -> None:
    payload = report_entry_to_payload(
        ClaimReportEntry(
            claim_id="claim-conflict-only",
            case_id="case-1",
            final_verdict=VerificationVerdict.CONTRADICT,
            human_review_status=HumanReviewStatus.UNREVIEWED,
            summary_text="Only contradicting chunks were selected.",
            supporting_chunk_ids=(),
            contradicting_chunk_ids=("chunk-contradict-only",),
        )
    )

    assert payload["citation_quality_flags"] == ["contradiction_without_support"]


def test_report_payload_includes_review_queue_signals() -> None:
    outcome = ReportAssemblyOutcome(
        request=ReportAssemblyRequest(
            case_id="case-queue",
            review_decisions=(
                ClaimReviewDecision(
                    claim_id="claim-excluded",
                    case_id="case-queue",
                    human_review_status=HumanReviewStatus.EXCLUDED,
                    analyst_disposition=AnalystDisposition.EXCLUDE_FROM_REPORT,
                    final_verdict=VerificationVerdict.SUPPORT,
                    review_notes="Do not publish.",
                ),
            ),
        ),
        entries=(
            ClaimReportEntry(
                claim_id="claim-conflict",
                case_id="case-queue",
                final_verdict=VerificationVerdict.CONTRADICT,
                human_review_status=HumanReviewStatus.UNREVIEWED,
                summary_text="Conflicting evidence needs analyst review.",
                supporting_chunk_ids=("chunk-support",),
                contradicting_chunk_ids=("chunk-contradict",),
            ),
            ClaimReportEntry(
                claim_id="claim-insufficient",
                case_id="case-queue",
                final_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
                human_review_status=HumanReviewStatus.UNREVIEWED,
                summary_text="Grounding still insufficient.",
                supporting_chunk_ids=(),
                contradicting_chunk_ids=(),
            ),
            ClaimReportEntry(
                claim_id="claim-excluded",
                case_id="case-queue",
                final_verdict=VerificationVerdict.SUPPORT,
                human_review_status=HumanReviewStatus.EXCLUDED,
                summary_text="Excluded from report.",
                supporting_chunk_ids=("chunk-excluded",),
                contradicting_chunk_ids=(),
            ),
        ),
        case_report=CaseReport(
            case_id="case-queue",
            generated_claim_ids=(
                "claim-conflict",
                "claim-insufficient",
                "claim-excluded",
            ),
            entries=(),
            report_summary="Queue test report.",
        ),
    )

    payload = report_outcome_to_payload(outcome)
    markdown = render_report_markdown(outcome)
    case_report = cast(dict[str, object], payload["case_report"])
    review_queue_signals = cast(
        dict[str, object],
        case_report["review_queue_signals"],
    )
    verification_summary = cast(
        dict[str, object],
        case_report["verification_summary"],
    )

    assert review_queue_signals == {
        "review_required_claim_count": 2,
        "reason_buckets": {
            "conflicting_evidence": 1,
            "no_verified_support": 1,
        },
        "priority_buckets": {
            "high": 1,
            "normal": 1,
        },
        "rationale_class_summary": {
            "conflict_driven": 1,
            "no_support_driven": 1,
        },
        "priority_rationale": [
            {
                "claim_id": "claim-conflict",
                "priority": "high",
                "gate_reason": "conflicting_evidence",
                "support_rationale": "conflicting_evidence",
                "citation_quality_flags": ["mixed_support_and_contradiction"],
                "rationale_flags": [
                    "gate_reason_conflicting_evidence",
                    "mixed_support_and_contradiction",
                ],
            },
            {
                "claim_id": "claim-insufficient",
                "priority": "normal",
                "gate_reason": "no_verified_support",
                "support_rationale": "unsupported_or_not_applicable",
                "citation_quality_flags": [],
                "rationale_flags": [],
            },
        ],
    }
    assert verification_summary["support_rationale_summary"] == {
        "exact_lexical_match_count": 0,
        "corroborated_partial_hits_count": 0,
        "conflicting_evidence_count": 1,
        "unsupported_or_not_applicable_count": 1,
    }
    assert verification_summary["contradiction_diagnostics"] == {
        "contradicted_claim_count": 1,
        "contradicting_chunk_count": 1,
        "claims_with_mixed_support_and_contradiction_count": 1,
    }
    assert "## Review queue rationale" in markdown
    assert "- Review-required claims: 2" in markdown
    assert "- Priority buckets: high=1, normal=1" in markdown
    assert "- Rationale classes: conflict driven=1, no support driven=1" in markdown
    assert (
        "- Claim claim-conflict: priority=high, gate reason=conflicting evidence, "
        "support rationale=conflicting evidence, "
        "citation flags=mixed support and contradiction, "
        "rationale flags=gate reason conflicting evidence, mixed support and contradiction"
    ) in markdown
    assert (
        "- Claim claim-insufficient: priority=normal, gate reason=no verified support, "
        "support rationale=unsupported or not applicable, citation flags=none, rationale flags=none"
    ) in markdown


def test_verification_payload_marks_excluded_review_as_blocked() -> None:
    delivery = _seeded_delivery()
    delivery.verify_claim(VerificationDeliveryRequest(claim=_claim(), requested_k=2))
    delivery.record_review(
        ClaimReviewDecision(
            claim_id="claim-1",
            case_id="case-1",
            human_review_status=HumanReviewStatus.EXCLUDED,
            analyst_disposition=AnalystDisposition.EXCLUDE_FROM_REPORT,
            final_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
            review_notes="Excluded from publication.",
        )
    )

    verification = delivery.persistence.claims.get_verification("claim-1")
    assert verification is not None
    outcome = delivery.inspect_verification("claim-1")
    assert outcome is not None
    verification_payload = verification_to_payload(verification, outcome.review_decision)

    assert verification_payload["publication_gate"] == "blocked"
    assert verification_payload["gate_reason"] == "human_review_excluded"
    assert verification_payload["support_signals_present"] is True
    assert verification_payload["conflict_signals_present"] is False
    assert verification_payload["evidence_count"] == 1
    assert verification_payload["citation_quality_flags"] == []
    assert outcome.support_rationale == "exact_lexical_match"
    inspection_payload = verification_inspection_to_payload(outcome)
    assert inspection_payload["support_rationale"] == "exact_lexical_match"
    assert (
        verification_payload["sufficiency_summary"]
        == "Supporting evidence found in 1 retrieved chunk."
    )
    assert outcome.verification.verdict is VerificationVerdict.SUPPORT


def test_verification_inspection_payload_includes_previously_fact_checked_matches() -> None:
    delivery = _seeded_delivery()
    delivery.verify_claim(VerificationDeliveryRequest(claim=_claim(), requested_k=2))
    duplicate_claim = delivery.persistence.claims.save_claims(
        (
            Claim(
                claim_id="claim-2",
                case_id="case-1",
                document_id="doc-1",
                chunk_id="chunk-1",
                exact_text="  the BRIDGE reopened after inspection. ",
                source_span_reference="p1",
                system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
                rationale=None,
            ),
        )
    )[0]
    delivery.persistence.claims.save_verification(
        ClaimVerification(
            claim_id=duplicate_claim.claim_id,
            case_id=duplicate_claim.case_id,
            verdict=VerificationVerdict.SUPPORT,
            supporting_chunk_ids=("chunk-1",),
            contradicting_chunk_ids=(),
            analyst_notes="matched previous support",
        )
    )
    delivery.record_review(
        ClaimReviewDecision(
            claim_id=duplicate_claim.claim_id,
            case_id=duplicate_claim.case_id,
            human_review_status=HumanReviewStatus.REVIEWED_ACCEPT,
            analyst_disposition=AnalystDisposition.CONFIRMED_SUPPORT,
            final_verdict=VerificationVerdict.SUPPORT,
            review_notes="Previously confirmed claim.",
        )
    )

    inspection = delivery.inspect_verification("claim-1")
    assert inspection is not None

    payload = verification_inspection_to_payload(inspection)

    assert payload["previously_fact_checked_matches"] == [
        {
            "claim_id": "claim-2",
            "case_id": "case-1",
            "exact_text": "  the BRIDGE reopened after inspection. ",
            "human_review_status": "reviewed_accept",
            "final_verdict": "support",
            "normalization_risk_flags": [
                "whitespace_normalized_match",
            ],
            "claim_type_signals": [],
        }
    ]


def test_verification_inspection_payload_flags_diacritic_normalized_match_risk() -> None:
    delivery = _seeded_delivery()
    delivery.verify_claim(VerificationDeliveryRequest(claim=_claim(), requested_k=2))
    duplicate_claim = delivery.persistence.claims.save_claims(
        (
            Claim(
                claim_id="claim-3",
                case_id="case-1",
                document_id="doc-1",
                chunk_id="chunk-1",
                exact_text="The brídge reopened after inspection.",
                source_span_reference="p1",
                system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
                rationale=None,
            ),
        )
    )[0]
    delivery.persistence.claims.save_verification(
        ClaimVerification(
            claim_id=duplicate_claim.claim_id,
            case_id=duplicate_claim.case_id,
            verdict=VerificationVerdict.SUPPORT,
            supporting_chunk_ids=("chunk-1",),
            contradicting_chunk_ids=(),
            analyst_notes="matched after diacritic stripping",
        )
    )

    inspection = delivery.inspect_verification("claim-1")
    assert inspection is not None

    payload = verification_inspection_to_payload(inspection)

    assert payload["previously_fact_checked_matches"] == [
        {
            "claim_id": "claim-3",
            "case_id": "case-1",
            "exact_text": "The brídge reopened after inspection.",
            "human_review_status": None,
            "final_verdict": "support",
            "normalization_risk_flags": ["diacritic_stripped_match"],
            "claim_type_signals": [],
        }
    ]


def test_verification_inspection_payload_flags_numeric_and_temporal_claim_types() -> None:
    delivery = _seeded_delivery()
    numeric_claim = delivery.persistence.claims.save_claims(
        (
            Claim(
                claim_id="claim-4",
                case_id="case-1",
                document_id="doc-1",
                chunk_id="chunk-1",
                exact_text="Revenue increased by 12% in 2024.",
                source_span_reference="p1",
                system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
                rationale=None,
            ),
        )
    )[0]
    delivery.persistence.claims.save_verification(
        ClaimVerification(
            claim_id=numeric_claim.claim_id,
            case_id=numeric_claim.case_id,
            verdict=VerificationVerdict.SUPPORT,
            supporting_chunk_ids=("chunk-1",),
            contradicting_chunk_ids=(),
            analyst_notes="matched numeric temporal claim",
        )
    )

    inspection = VerificationInspection(
        claim=numeric_claim,
        verification=ClaimVerification(
            claim_id=numeric_claim.claim_id,
            case_id=numeric_claim.case_id,
            verdict=VerificationVerdict.SUPPORT,
            supporting_chunk_ids=("chunk-1",),
            contradicting_chunk_ids=(),
            analyst_notes="supported numeric temporal claim",
        ),
        review_decision=None,
        evidence_links=(),
        evidence_count=0,
        supporting_evidence_count=0,
        contradicting_evidence_count=0,
        insufficient_evidence_count=0,
        has_review=False,
        has_report_entry=False,
        support_rationale="corroborated_partial_hits",
        previously_fact_checked_matches=(
            {
                "claim_id": "claim-4",
                "case_id": "case-1",
                "exact_text": "Revenue increased by 12% in 2024.",
                "human_review_status": None,
                "final_verdict": "support",
                "normalization_risk_flags": [],
                "claim_type_signals": ["numeric_claim", "temporal_claim"],
            },
        ),
    )

    payload = verification_inspection_to_payload(inspection)

    assert payload["support_rationale"] == "corroborated_partial_hits"
    assert payload["previously_fact_checked_matches"] == [
        {
            "claim_id": "claim-4",
            "case_id": "case-1",
            "exact_text": "Revenue increased by 12% in 2024.",
            "human_review_status": None,
            "final_verdict": "support",
            "normalization_risk_flags": [],
            "claim_type_signals": ["numeric_claim", "temporal_claim"],
        }
    ]


def test_verification_payload_without_evidence_link_context_does_not_guess_missing_best_evidence() -> None:
    payload = verification_to_payload(
        ClaimVerification(
            claim_id="claim-1",
            case_id="case-1",
            verdict=VerificationVerdict.SUPPORT,
            supporting_chunk_ids=("chunk-1",),
            contradicting_chunk_ids=(),
            analyst_notes="supported",
        )
    )

    assert payload["citation_quality_flags"] == []


def test_verification_payload_flags_non_retrieval_and_redundant_citation() -> None:
    payload = verification_to_payload(
        ClaimVerification(
            claim_id="claim-1",
            case_id="case-1",
            verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
            supporting_chunk_ids=(),
            contradicting_chunk_ids=(),
            analyst_notes="no retrieved support",
        ),
        evidence_links=(
            ClaimEvidenceLink(
                claim_id="claim-1",
                document_id="doc-1",
                chunk_id="chunk-1",
                evidence_rank=1,
                evidence_verdict=VerificationVerdict.SUPPORT,
                rationale="manual citation",
                snippet="supporting text",
                score=None,
            ),
            ClaimEvidenceLink(
                claim_id="claim-1",
                document_id="doc-1",
                chunk_id="chunk-1",
                evidence_rank=2,
                evidence_verdict=VerificationVerdict.SUPPORT,
                rationale="duplicate citation",
                snippet="supporting text",
                score=None,
            ),
        ),
    )

    assert payload["citation_quality_flags"] == [
        "non_retrieval_attributable",
        "redundant_citation",
    ]


def test_verification_inspection_payload_includes_top_two_best_evidence_links() -> None:
    inspection = VerificationInspection(
        claim=_claim(),
        verification=ClaimVerification(
            claim_id="claim-1",
            case_id="case-1",
            verdict=VerificationVerdict.SUPPORT,
            supporting_chunk_ids=("chunk-2", "chunk-1"),
            contradicting_chunk_ids=(),
            analyst_notes="supported",
        ),
        review_decision=None,
        evidence_links=(
            ClaimEvidenceLink(
                claim_id="claim-1",
                document_id="doc-1",
                chunk_id="chunk-2",
                evidence_rank=2,
                evidence_verdict=VerificationVerdict.SUPPORT,
                rationale="second-best",
                snippet="second snippet",
                score=0.7,
            ),
            ClaimEvidenceLink(
                claim_id="claim-1",
                document_id="doc-1",
                chunk_id="chunk-1",
                evidence_rank=1,
                evidence_verdict=VerificationVerdict.SUPPORT,
                rationale="best",
                snippet="best snippet",
                score=0.9,
            ),
            ClaimEvidenceLink(
                claim_id="claim-1",
                document_id="doc-1",
                chunk_id="chunk-3",
                evidence_rank=3,
                evidence_verdict=VerificationVerdict.SUPPORT,
                rationale="third-best",
                snippet="third snippet",
                score=0.4,
            ),
        ),
        evidence_count=3,
        supporting_evidence_count=3,
        contradicting_evidence_count=0,
        insufficient_evidence_count=0,
        has_review=False,
        has_report_entry=False,
    )

    payload = verification_inspection_to_payload(inspection)

    assert [item["chunk_id"] for item in payload["best_evidence"]] == ["chunk-1", "chunk-2"]
    assert [item["evidence_rank"] for item in payload["best_evidence"]] == [1, 2]
    assert payload["best_evidence"][0]["snippet"] == "best snippet"
    assert payload["best_evidence"][1]["snippet"] == "second snippet"
    assert payload["claim_trace_summary"] == {
        "final_verdict": "support",
        "evidence_sufficiency": "supported",
        "publication_gate": "allowed",
        "gate_reason": None,
        "sufficiency_summary": "Supporting evidence found in 2 retrieved chunks.",
        "citation_quality_flags": [],
        "best_evidence": payload["best_evidence"],
        "review_note": "supported",
    }
    assert payload["verification_trace_log"] == {
        "retrieval_trace": {
            "query_text": "The bridge reopened after inspection.",
            "considered_chunks": [
                {
                    "chunk_id": "chunk-2",
                    "document_id": "doc-1",
                    "evidence_rank": 2,
                    "evidence_verdict": "support",
                    "score": 0.7,
                },
                {
                    "chunk_id": "chunk-1",
                    "document_id": "doc-1",
                    "evidence_rank": 1,
                    "evidence_verdict": "support",
                    "score": 0.9,
                },
                {
                    "chunk_id": "chunk-3",
                    "document_id": "doc-1",
                    "evidence_rank": 3,
                    "evidence_verdict": "support",
                    "score": 0.4,
                },
            ],
            "selected_supporting_chunks": ["chunk-2", "chunk-1"],
            "selected_contradicting_chunks": [],
        },
        "decision_trace": {
            "verdict": "support",
            "evidence_sufficiency": "supported",
            "publication_gate": "allowed",
            "gate_reason": None,
            "sufficiency_summary": "Supporting evidence found in 2 retrieved chunks.",
            "contradiction_trace": {
                "selected_contradicting_chunks": [],
                "contradicting_evidence_count": 0,
                "best_contradicting_evidence": [],
            },
        },
        "review_trace": {
            "has_review": False,
            "review_status": None,
            "review_verdict": None,
            "review_notes": None,
        },
    }


def test_verification_inspection_payload_includes_contradiction_trace() -> None:
    inspection = VerificationInspection(
        claim=_claim(),
        verification=ClaimVerification(
            claim_id="claim-1",
            case_id="case-1",
            verdict=VerificationVerdict.CONTRADICT,
            supporting_chunk_ids=(),
            contradicting_chunk_ids=("chunk-conflict",),
            analyst_notes="contradicted by retrieved evidence",
        ),
        review_decision=None,
        evidence_links=(
            ClaimEvidenceLink(
                claim_id="claim-1",
                document_id="doc-1",
                chunk_id="chunk-conflict",
                evidence_rank=1,
                evidence_verdict=VerificationVerdict.CONTRADICT,
                rationale="directly refutes claim",
                snippet="The bridge remained closed pending inspection.",
                score=0.95,
            ),
            ClaimEvidenceLink(
                claim_id="claim-1",
                document_id="doc-1",
                chunk_id="chunk-support-ish",
                evidence_rank=2,
                evidence_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
                rationale="mentions bridge but not reopening",
                snippet="Officials discussed the bridge status.",
                score=0.4,
            ),
        ),
        evidence_count=2,
        supporting_evidence_count=0,
        contradicting_evidence_count=1,
        insufficient_evidence_count=1,
        has_review=False,
        has_report_entry=False,
        support_rationale="conflicting_evidence",
    )

    payload = verification_inspection_to_payload(inspection)
    verification_trace_log = cast(dict[str, object], payload["verification_trace_log"])
    decision_trace = cast(dict[str, object], verification_trace_log["decision_trace"])
    contradiction_trace = cast(dict[str, object], decision_trace["contradiction_trace"])

    assert payload["support_rationale"] == "conflicting_evidence"
    assert contradiction_trace == {
        "selected_contradicting_chunks": ["chunk-conflict"],
        "contradicting_evidence_count": 1,
        "best_contradicting_evidence": [
            {
                "claim_id": "claim-1",
                "document_id": "doc-1",
                "chunk_id": "chunk-conflict",
                "evidence_rank": 1,
                "evidence_verdict": "contradict",
                "rationale": "directly refutes claim",
                "snippet": "The bridge remained closed pending inspection.",
                "score": 0.95,
            }
        ],
    }


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
    verify_payload = json.loads(verify_body)
    assert verify_payload["verification"]["verdict"] == "support"
    assert verify_payload["verification"]["evidence_sufficiency"] == "supported"
    assert verify_payload["verification"]["publication_gate"] == "allowed"
    assert verify_payload["verification"]["gate_reason"] is None
    assert verify_payload["verification"]["support_signals_present"] is True
    assert verify_payload["verification"]["conflict_signals_present"] is False
    assert verify_payload["verification"]["evidence_count"] == 1
    assert (
        verify_payload["verification"]["sufficiency_summary"]
        == "Supporting evidence found in 1 retrieved chunk."
    )
    assert inspect_status == "200 OK"
    inspection_payload = json.loads(inspect_body)
    assert inspection_payload["verification"]["evidence_sufficiency"] == "supported"
    assert inspection_payload["verification"]["publication_gate"] == "allowed"
    assert inspection_payload["verification"]["gate_reason"] is None
    assert inspection_payload["verification"]["support_signals_present"] is True
    assert inspection_payload["verification"]["conflict_signals_present"] is False
    assert inspection_payload["verification"]["evidence_count"] == 1
    assert (
        inspection_payload["verification"]["sufficiency_summary"]
        == "Supporting evidence found in 1 retrieved chunk."
    )
    assert inspection_payload["evidence_links"][0]["chunk_id"] == "chunk-1"
    assert inspection_payload["best_evidence"] == [inspection_payload["evidence_links"][0]]
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
    assert "<h2>Verification summary</h2>" in case_body
    assert "Evidence sufficiency:</strong> supported=1" in case_body
    assert "Publication gate:</strong> allowed=1" in case_body
    assert "Gate reason:</strong> none=1" in case_body
    assert "Allowed claims:</strong> 1" in case_body
    assert "Evidence sufficiency: supported" in case_body
    assert "Publication gate: allowed" in case_body
    assert "Gate reason: none" in case_body
    assert "Support signals present: yes" in case_body
    assert "Conflict signals present: no" in case_body
    assert "Evidence count: 1" in case_body
    assert "Sufficiency summary: Supporting evidence found in 1 retrieved chunk." in case_body
    assert "Best evidence: #1 [support] chunk-1:" in case_body


def test_wsgi_root_route_returns_html_home_page() -> None:
    app = create_wsgi_app(delivery=_seeded_delivery())

    status, headers, body = _call_wsgi(app, method="GET", path="/")

    assert status == "200 OK"
    assert ("Content-Type", "text/html; charset=utf-8") in headers
    assert "SourceTrace local server" in body
    assert "POST /api/verify" in body


def test_wsgi_app_exposes_configured_credibility_assessment_route() -> None:
    persistence = create_in_memory_persistence()
    persistence.documents.save_document(_document())
    prompts: list[str] = []

    def draft_credibility(prompt: str) -> LlmGenerationResult:
        prompts.append(prompt)
        return LlmGenerationResult(
            text=(
                '{"summary":"Source is tentative.",' 
                '"strengths":["Named publisher"],' 
                '"concerns":["No raw dataset linked"],' 
                '"verification_checks":["Find the original filing"],' 
                '"source_reliability":"medium",' 
                '"information_credibility":"low",' 
                '"source_reliability_factors":["named_publisher"],' 
                '"information_credibility_factors":["raw_dataset_missing"],' 
                '"provenance_distance":"secondary"}'
            ),
            model="gpt-4.1-mini",
        )

    delivery = create_default_delivery(
        persistence=persistence,
        credibility_draft=draft_credibility,
        credibility_assessed_at=lambda: datetime(2026, 5, 18, 0, 10, tzinfo=UTC),
    )
    app = create_wsgi_app(delivery=delivery)

    status, _, body = _call_wsgi(
        app,
        method="POST",
        path="/api/documents/doc-1/credibility",
        payload={"assessment_method": "llm_draft_v1"},
    )

    payload = json.loads(body)
    assert status == "200 OK"
    assert payload["credibility_assessment"] == {
        "assessment_id": "credibility-doc-1",
        "document_id": "doc-1",
        "source_reliability": "medium",
        "information_credibility": "low",
        "source_reliability_factors": ["named_publisher"],
        "information_credibility_factors": ["raw_dataset_missing"],
        "provenance_distance": "secondary",
        "method": "llm_draft_v1",
        "notes": "Summary: Source is tentative.\nStrengths: Named publisher\nConcerns: No raw dataset linked\nVerification checks: Find the original filing",
        "summary": "Source is tentative.",
        "strengths": ["Named publisher"],
        "concerns": ["No raw dataset linked"],
        "verification_checks": ["Find the original filing"],
        "assessed_by": "system",
        "assessed_at": "2026-05-18T00:10:00+00:00",
        "override": False,
    }
    assert "doc-1" in prompts[0]


def test_wsgi_app_can_seed_document_then_run_credibility_assessment_route() -> None:
    prompts: list[str] = []

    def draft_credibility(prompt: str) -> LlmGenerationResult:
        prompts.append(prompt)
        return LlmGenerationResult(
            text="Seeded credibility note.",
            model="gpt-4.1-mini",
        )

    app = create_wsgi_app(
        delivery=create_default_delivery(
            credibility_draft=draft_credibility,
            credibility_assessed_at=lambda: datetime(2026, 5, 19, 9, 50, tzinfo=UTC),
        )
    )

    seed_status, seed_headers, seed_body = _call_wsgi(
        app,
        method="POST",
        path="/api/dev/documents",
        payload={
            "document_id": "doc-1",
            "case_id": "case-1",
            "source_type": "url",
            "source_url": "https://example.test/report",
            "publisher": "Example News",
            "author": "Analyst",
            "title": "Network report",
            "published_at": "2026-05-18T00:00:00+00:00",
            "retrieved_at": "2026-05-18T00:05:00+00:00",
            "content_hash": "sha256:abc123",
            "language": "en",
        },
    )
    status, headers, body = _call_wsgi(
        app,
        method="POST",
        path="/api/documents/doc-1/credibility",
        payload={"assessment_method": "llm_draft_v1"},
    )

    assert seed_status == "201 Created"
    assert ("Content-Type", "application/json; charset=utf-8") in seed_headers
    assert json.loads(seed_body) == {
        "document": {
            "document_id": "doc-1",
            "case_id": "case-1",
            "source_type": "url",
            "source_url": "https://example.test/report",
            "publisher": "Example News",
            "author": "Analyst",
            "title": "Network report",
            "published_at": "2026-05-18T00:00:00+00:00",
            "retrieved_at": "2026-05-18T00:05:00+00:00",
            "content_hash": "sha256:abc123",
            "language": "en",
            "has_inline_content": False,
        }
    }
    assert status == "200 OK"
    assert ("Content-Type", "application/json; charset=utf-8") in headers
    assert "doc-1" in prompts[0]
    assert json.loads(body)["credibility_assessment"] == {
        "assessment_id": "credibility-doc-1",
        "document_id": "doc-1",
        "source_reliability": "unknown",
        "information_credibility": "unknown",
        "source_reliability_factors": [],
        "information_credibility_factors": [],
        "provenance_distance": "unknown",
        "method": "llm_draft_v1",
        "notes": "Seeded credibility note.",
        "summary": None,
        "strengths": [],
        "concerns": [],
        "verification_checks": [],
        "assessed_by": "system",
        "assessed_at": "2026-05-19T09:50:00+00:00",
        "override": False,
    }


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


def test_wsgi_app_create_case_generates_case_id_when_missing() -> None:
    app = create_wsgi_app(delivery=create_default_delivery())

    status, _, body = _call_wsgi(
        app,
        method="POST",
        path="/api/cases",
        payload={"title": "Local SourceTrace smoke test", "description": "desc"},
    )

    payload = json.loads(body)
    assert status == "201 Created"
    assert payload["case"]["title"] == "Local SourceTrace smoke test"
    assert payload["case"]["description"] == "desc"
    assert payload["case"]["case_id"].startswith("case-")
    assert payload["case_id"] == payload["case"]["case_id"]


def test_wsgi_app_attach_document_accepts_minimal_inline_payload_and_prepare_uses_document_content() -> None:
    app = create_wsgi_app(delivery=create_default_delivery())

    case_status, _, case_body = _call_wsgi(
        app,
        method="POST",
        path="/api/cases",
        payload={"title": "Apollo case"},
    )
    case_id = json.loads(case_body)["case"]["case_id"]

    create_status, _, create_body = _call_wsgi(
        app,
        method="POST",
        path=f"/api/cases/{case_id}/documents",
        payload={
            "title": "Apollo note",
            "content": "Apollo 11 landed on the Moon in 1969. Neil Armstrong walked on the Moon.",
        },
    )
    create_payload = json.loads(create_body)
    document_id = create_payload["document_id"]

    prepare_status, _, prepare_body = _call_wsgi(
        app,
        method="POST",
        path=f"/api/documents/{document_id}/prepare",
        payload={},
    )

    prepare_payload = json.loads(prepare_body)
    assert case_status == "201 Created"
    assert create_status == "201 Created"
    assert create_payload["document_id"] == document_id
    assert prepare_status == "200 OK"
    assert prepare_payload["status"] == "ready"
    assert prepare_payload["document"]["document_id"] == document_id
    assert len(prepare_payload["chunks"]) >= 1
    assert "Apollo 11 landed on the Moon in 1969." in prepare_payload["chunks"][0]["raw_text"]


def test_wsgi_app_attach_document_accepts_text_alias_and_prepare_without_body_reuses_inline_content() -> None:
    app = create_wsgi_app(delivery=create_default_delivery())

    case_status, _, case_body = _call_wsgi(
        app,
        method="POST",
        path="/api/cases",
        payload={"title": "Restart continuity case"},
    )
    case_id = json.loads(case_body)["case"]["case_id"]

    create_status, _, create_body = _call_wsgi(
        app,
        method="POST",
        path=f"/api/cases/{case_id}/documents",
        payload={
            "title": "Restart test document",
            "text": "OpenAI announced a major partnership with Example University to improve AI safety research.",
            "source_type": "web_article",
            "source_url": "https://example.com/restart-test",
            "content_hash": "sha256:test-inline-restart",
        },
    )
    create_payload = json.loads(create_body)
    document_id = create_payload["document_id"]

    prepare_status, _, prepare_body = _call_wsgi(
        app,
        method="POST",
        path=f"/api/documents/{document_id}/prepare",
        payload={},
    )

    prepare_payload = json.loads(prepare_body)
    assert case_status == "201 Created"
    assert create_status == "201 Created"
    assert create_payload["status"] == "ready"
    assert create_payload["document_id"] == document_id
    assert prepare_status == "200 OK"
    assert prepare_payload["status"] == "ready"
    assert prepare_payload["resource"] == "document_preparation"
    assert prepare_payload["resource_id"] == document_id
    assert prepare_payload["next_step"] == f"POST /api/documents/{document_id}/extract-claims"
    assert len(prepare_payload["chunks"]) >= 1
    assert "OpenAI announced a major partnership" in prepare_payload["chunks"][0]["raw_text"]


def test_wsgi_extract_claims_route_auto_prepares_inline_content_when_chunks_are_missing() -> None:
    app = create_wsgi_app(
        delivery=create_default_delivery(
            claim_extraction=lambda prepared_text: LlmStructuredGenerationResult(
                payload={
                    "claims": [
                        {
                            "claim": "Heavy trucks remain barred until next week.",
                            "exact_text": "Heavy trucks remain barred until next week.",
                        }
                    ]
                },
                model="gpt-test",
            )
        )
    )

    case_status, _, case_body = _call_wsgi(
        app,
        method="POST",
        path="/api/cases",
        payload={"title": "Contrast auto-prepare case"},
    )
    case_id = json.loads(case_body)["case"]["case_id"]

    create_status, _, create_body = _call_wsgi(
        app,
        method="POST",
        path=f"/api/cases/{case_id}/documents",
        payload={
            "title": "Contrast auto-prepare document",
            "text": (
                "Although the bridge reopened to cars on Tuesday, heavy trucks remain barred until next week. "
                "Officials said freight inspections are still underway."
            ),
            "source_type": "note",
            "source_url": "https://example.test/contrast-auto-prepare",
            "content_hash": "sha256:contrast-auto-prepare",
        },
    )
    create_payload = json.loads(create_body)
    document_id = create_payload["document_id"]

    extract_status, _, extract_body = _call_wsgi(
        app,
        method="POST",
        path=f"/api/documents/{document_id}/extract-claims",
        payload={},
    )
    extract_payload = json.loads(extract_body)

    chunks_status, _, chunks_body = _call_wsgi(
        app,
        method="GET",
        path=f"/api/documents/{document_id}/chunks",
    )
    chunks_payload = json.loads(chunks_body)

    assert case_status == "201 Created"
    assert create_status == "201 Created"
    assert extract_status == "200 OK"
    assert extract_payload["diagnostics"]["chunk_count"] >= 1
    assert extract_payload["claims"][0]["exact_text"] == "Heavy trucks remain barred until next week."
    assert chunks_status == "200 OK"
    assert len(chunks_payload["chunks"]) >= 1
    assert "heavy trucks remain barred until next week" in chunks_payload["chunks"][0]["raw_text"].lower()



def test_render_case_review_html_shows_document_snippet_preview() -> None:
    delivery = create_default_delivery()
    delivery.persistence.cases.save_case(
        Case(case_id="case-snippet", title="Snippet case", description="HTML preview")
    )
    delivery.persistence.documents.save_document(
        Document(
            document_id="doc-snippet",
            case_id="case-snippet",
            source_type="inline_text",
            source_url=None,
            publisher=None,
            author=None,
            title="Snippet doc",
            published_at=None,
            retrieved_at=datetime(2026, 5, 20, 12, 0, tzinfo=UTC),
            content_hash="sha256:snippet",
            language="en",
            inline_content="OpenAI announced a major partnership with Example University to improve AI safety research. The announcement described a multi-year research program and related governance commitments.",
        )
    )

    html = render_case_review_html(delivery, "case-snippet")

    assert "Snippet doc" in html
    assert "Snippet:" in html
    assert "OpenAI announced a major partnership with Example University" in html
    assert "..." in html
    assert "Status:" in html
    assert "Not assessed yet." in html
    assert "POST /api/documents/doc-snippet/credibility" in html


def test_render_case_review_html_shows_support_rationale() -> None:
    delivery = _seeded_delivery()
    delivery.verify_claim(VerificationDeliveryRequest(claim=_claim(), requested_k=2))

    html = render_case_review_html(delivery, "case-1")

    assert "Support rationale counts:" in html
    assert "exact lexical match=1, corroborated partial hits=0, conflicting evidence=0, unsupported or not applicable=0" in html
    assert "Contradiction diagnostics:" in html
    assert "contradicted_claim_count=0, contradicting_chunk_count=0, claims_with_mixed_support_and_contradiction_count=0" in html
    assert "Support rationale: exact lexical match" in html
    assert "Contradiction snippet: No contradicting chunks selected." in html
    assert "Citation quality flags: none" in html
    assert "Priority rationale classes:" in html
    assert "Priority rationale:" in html
    assert "Queue status:" in html
    assert "no review-required claims" in html


def test_render_case_review_html_shows_review_queue_priority_rationale() -> None:
    delivery = create_default_delivery()
    delivery.persistence.cases.save_case(
        Case(case_id="case-queue-html", title="Queue HTML case", description="Queue review html")
    )
    delivery.persistence.documents.save_document(
        Document(
            document_id="doc-queue-html",
            case_id="case-queue-html",
            source_type="url",
            source_url="https://example.test/queue-html",
            publisher="Queue News",
            author="Analyst",
            title="Queue HTML doc",
            published_at=datetime(2026, 5, 18, 0, 0, tzinfo=UTC),
            retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
            content_hash="sha256:queue-html",
            language="en",
        )
    )
    conflict_claim = Claim(
        claim_id="claim-conflict-html",
        case_id="case-queue-html",
        document_id="doc-queue-html",
        chunk_id="chunk-support",
        exact_text="Bridge reopened after inspection.",
        source_span_reference="p1",
        system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
    )
    insufficient_claim = Claim(
        claim_id="claim-insufficient-html",
        case_id="case-queue-html",
        document_id="doc-queue-html",
        chunk_id="chunk-missing",
        exact_text="Timetable was available.",
        source_span_reference="p2",
        system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=None,
    )
    delivery.persistence.claims.save_claims((conflict_claim, insufficient_claim))
    delivery.persistence.claims.save_verification(
        ClaimVerification(
            claim_id="claim-conflict-html",
            case_id="case-queue-html",
            verdict=VerificationVerdict.CONTRADICT,
            supporting_chunk_ids=("chunk-support",),
            contradicting_chunk_ids=("chunk-contradict",),
            analyst_notes="conflict",
        )
    )
    delivery.persistence.claims.save_verification(
        ClaimVerification(
            claim_id="claim-insufficient-html",
            case_id="case-queue-html",
            verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
            supporting_chunk_ids=(),
            contradicting_chunk_ids=(),
            analyst_notes="missing support",
        )
    )
    delivery.record_review(
        ClaimReviewDecision(
            claim_id="claim-conflict-html",
            case_id="case-queue-html",
            human_review_status=HumanReviewStatus.REVIEWED_OVERRIDE,
            analyst_disposition=AnalystDisposition.CONFIRMED_CONTRADICTION,
            final_verdict=VerificationVerdict.CONTRADICT,
            review_notes="conflict review",
        )
    )
    delivery.record_review(
        ClaimReviewDecision(
            claim_id="claim-insufficient-html",
            case_id="case-queue-html",
            human_review_status=HumanReviewStatus.NEEDS_FOLLOWUP,
            analyst_disposition=AnalystDisposition.INSUFFICIENT_EVIDENCE,
            final_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
            review_notes="insufficient review",
        )
    )

    html = render_case_review_html(delivery, "case-queue-html")

    assert "Priority rationale:" in html
    assert "claim-conflict-html" in html
    assert "Priority rationale classes:" in html
    assert "conflict driven=1, no support driven=1" in html
    assert "priority=high, gate reason=conflicting evidence, support rationale=conflicting evidence" in html
    assert "citation flags=mixed support and contradiction" in html
    assert "rationale flags=gate reason conflicting evidence, mixed support and contradiction" in html
    assert "claim-insufficient-html" in html
    assert "priority=normal, gate reason=no verified support, support rationale=unsupported or not applicable" in html


def test_document_from_payload_slugifies_polish_title_to_ascii_safe_document_id() -> None:
    from sourcetrace.web.delivery import document_from_payload

    document = document_from_payload(
        {
            "case_id": "case-1",
            "title": "Artykuł: autobusy elektryczne",
            "content": "Treść testowa.",
        }
    )

    assert document.document_id == "doc-artykul-autobusy-elektryczne"


def test_wsgi_app_missing_document_credibility_route_reports_document_not_found() -> None:
    app = create_wsgi_app(delivery=create_default_delivery())

    status, _, body = _call_wsgi(
        app,
        method="POST",
        path="/api/documents/missing-doc/credibility",
        payload={},
    )

    assert status == "404 Not Found"
    assert json.loads(body) == {"error": "document_not_found", "status": "missing"}


def _seeded_delivery() -> SourceTraceDelivery:
    persistence = create_in_memory_persistence()
    persistence.cases.save_case(
        Case(
            case_id="case-1",
            title="Bridge case",
            description="Seeded test case.",
        )
    )
    persistence.documents.save_document(_document())
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


def _document() -> Document:
    return Document(
        document_id="doc-1",
        case_id="case-1",
        source_type="url",
        source_url="https://example.test/report",
        publisher="Example News",
        author="Analyst",
        title="Network report",
        published_at=datetime(2026, 5, 18, 0, 0, tzinfo=UTC),
        retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
        content_hash="sha256:abc123",
        language="en",
    )


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
