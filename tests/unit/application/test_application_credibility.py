"""Application credibility assessment contract tests."""

import json
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from os import environ

import pytest

from sourcetrace.application import (
    CredibilityAssessmentExecution,
    CredibilityAssessmentOutcome,
    CredibilityAssessmentRequest,
    CredibilityAssessor,
    build_llm_credibility_assessor,
)
from sourcetrace.application.credibility import (
    CredibilityAssessmentOutcome as ModuleCredibilityAssessmentOutcome,
)
from sourcetrace.application.credibility import (
    CredibilityAssessmentRequest as ModuleCredibilityAssessmentRequest,
)
from sourcetrace.application.credibility_runtime import (
    build_llm_credibility_assessor as RuntimeBuildLlmCredibilityAssessor,
)
from sourcetrace.application.interfaces import (
    CredibilityAssessmentExecution as InterfacesCredibilityAssessmentExecution,
)
from sourcetrace.application.interfaces import (
    CredibilityAssessor as InterfacesCredibilityAssessor,
)
from sourcetrace.domain import Document, DocumentChunk, DocumentCredibilityAssessment
from sourcetrace.llm import LlmBootstrapConfig, LlmProfileConfig, LlmTaskConfig, SourceTraceLlmConfig, build_llm_runtime
from sourcetrace.llm.models import LlmGenerationResult
from sourcetrace.domain.types import CredibilityBand, ProvenanceDistance


def test_application_package_re_exports_credibility_assessment_contracts() -> None:
    assert CredibilityAssessmentRequest is ModuleCredibilityAssessmentRequest
    assert CredibilityAssessmentOutcome is ModuleCredibilityAssessmentOutcome
    assert CredibilityAssessor is InterfacesCredibilityAssessor
    assert CredibilityAssessmentExecution is InterfacesCredibilityAssessmentExecution
    assert build_llm_credibility_assessor is RuntimeBuildLlmCredibilityAssessor


def test_credibility_assessment_execution_bundle_keeps_explicit_callable_dependency() -> None:
    def assess_credibility(
        request: CredibilityAssessmentRequest,
    ) -> CredibilityAssessmentOutcome:
        assessment = DocumentCredibilityAssessment(
            assessment_id="cred-1",
            document_id=request.document.document_id,
            source_reliability=CredibilityBand.HIGH,
            information_credibility=CredibilityBand.MEDIUM,
            source_reliability_factors=("publisher_history",),
            information_credibility_factors=("partial_corroboration",),
            provenance_distance=ProvenanceDistance.PRIMARY,
            method=request.assessment_method or "rule_based_v1",
            notes="Needs analyst review before reporting.",
            assessed_by="system",
            assessed_at=datetime(2026, 5, 18, 0, 10, tzinfo=UTC),
            override=False,
        )
        return CredibilityAssessmentOutcome(request=request, assessment=assessment)

    execution = CredibilityAssessmentExecution(assess_credibility=assess_credibility)

    assert execution.assess_credibility is assess_credibility


def test_credibility_assessment_request_and_outcome_keep_document_and_assessment() -> None:
    document = Document(
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
    assessment = DocumentCredibilityAssessment(
        assessment_id="cred-1",
        document_id="doc-1",
        source_reliability=CredibilityBand.HIGH,
        information_credibility=CredibilityBand.MEDIUM,
        source_reliability_factors=("publisher_history",),
        information_credibility_factors=("partial_corroboration",),
        provenance_distance=ProvenanceDistance.PRIMARY,
        method="rule_based_v1",
        notes="Needs analyst review before reporting.",
        assessed_by="system",
        assessed_at=datetime(2026, 5, 18, 0, 10, tzinfo=UTC),
        override=False,
    )

    request = CredibilityAssessmentRequest(
        document=document,
        assessment_method="rule_based_v1",
    )
    outcome = CredibilityAssessmentOutcome(
        request=request,
        assessment=assessment,
    )

    assert outcome.request is request
    assert outcome.request.document is document
    assert outcome.assessment is assessment


def test_credibility_assessment_contracts_are_immutable() -> None:
    request = CredibilityAssessmentRequest(
        document=Document(
            document_id="doc-1",
            case_id="case-1",
            source_type="url",
            source_url="https://example.test/report",
            publisher=None,
            author=None,
            title=None,
            published_at=None,
            retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
            content_hash="sha256:abc123",
            language="en",
        )
    )

    with pytest.raises(FrozenInstanceError):
        setattr(request, "assessment_method", "other")


def test_build_llm_credibility_assessor_maps_draft_gateway_to_application_outcome() -> None:
    document = Document(
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
    prompts: list[str] = []

    def draft_credibility(prompt: str) -> LlmGenerationResult:
        prompts.append(prompt)
        return LlmGenerationResult(
            text="Corroborated by two independent reports.",
            model="gpt-4.1-mini",
            finish_reason="stop",
        )

    assessor = build_llm_credibility_assessor(
        draft_credibility=draft_credibility,
        assessed_at=lambda: datetime(2026, 5, 18, 0, 10, tzinfo=UTC),
    )
    request = CredibilityAssessmentRequest(
        document=document,
        assessment_method="llm_draft_v1",
    )

    outcome = assessor(request)

    assert outcome.request is request
    assert outcome.assessment.assessment_id == "credibility-doc-1"
    assert outcome.assessment.document_id == "doc-1"
    assert outcome.assessment.source_reliability is CredibilityBand.UNKNOWN
    assert outcome.assessment.information_credibility is CredibilityBand.UNKNOWN
    assert outcome.assessment.source_reliability_factors == ()
    assert outcome.assessment.information_credibility_factors == ()
    assert outcome.assessment.provenance_distance is ProvenanceDistance.UNKNOWN
    assert outcome.assessment.method == "llm_draft_v1"
    assert outcome.assessment.notes == "Corroborated by two independent reports."
    assert outcome.assessment.assessed_by == "system"
    assert outcome.assessment.assessed_at == datetime(2026, 5, 18, 0, 10, tzinfo=UTC)
    assert outcome.assessment.override is False
    assert "doc-1" in prompts[0]
    assert "Network report" in prompts[0]
    assert "https://example.test/report" in prompts[0]


def test_build_llm_credibility_assessor_normalizes_json_blob_into_human_readable_notes() -> None:
    document = Document(
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

    def draft_credibility(evidence_summary: str) -> LlmGenerationResult:
        return LlmGenerationResult(
            text=(
                '{"summary":"Lead only; provenance remains weak.",' 
                '"strengths":["Publisher is identified"],' 
                '"concerns":["No underlying dataset is linked"],' 
                '"verification_checks":["Confirm with the original ministry release"],' 
                '"source_reliability":"medium",' 
                '"information_credibility":"low",' 
                '"source_reliability_factors":["publisher_identified"],' 
                '"information_credibility_factors":["dataset_missing"],' 
                '"provenance_distance":"secondary"}'
            ),
            model="gpt-5.4",
            finish_reason="stop",
        )

    assessor = build_llm_credibility_assessor(
        draft_credibility=draft_credibility,
        assessed_at=lambda: datetime(2026, 5, 18, 0, 10, tzinfo=UTC),
    )

    outcome = assessor(
        CredibilityAssessmentRequest(document=document, assessment_method="llm_draft_v1")
    )

    assert outcome.assessment.notes == (
        "Summary: Lead only; provenance remains weak.\n"
        "Strengths: Publisher is identified\n"
        "Concerns: No underlying dataset is linked\n"
        "Verification checks: Confirm with the original ministry release"
    )
    assert outcome.assessment.summary == "Lead only; provenance remains weak."
    assert outcome.assessment.strengths == ("Publisher is identified",)
    assert outcome.assessment.concerns == ("No underlying dataset is linked",)
    assert outcome.assessment.verification_checks == (
        "Confirm with the original ministry release",
    )
    assert outcome.assessment.source_reliability is CredibilityBand.MEDIUM
    assert outcome.assessment.information_credibility is CredibilityBand.LOW
    assert outcome.assessment.source_reliability_factors == ("publisher_identified",)
    assert outcome.assessment.information_credibility_factors == ("dataset_missing",)
    assert outcome.assessment.provenance_distance is ProvenanceDistance.SECONDARY


def test_build_llm_credibility_assessor_normalizes_live_nested_json_blob_into_human_readable_notes() -> None:
    document = Document(
        document_id="doc-1",
        case_id="case-1",
        source_type="note",
        source_url=None,
        publisher=None,
        author=None,
        title="Climate analysis v2",
        published_at=None,
        retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
        content_hash="sha256:abc123",
        language="en",
    )

    def draft_credibility(evidence_summary: str) -> LlmGenerationResult:
        return LlmGenerationResult(
            text=json.dumps(
                {
                    "document_id": "doc-1",
                    "case_id": "case-1",
                    "source_type": "note",
                    "title": "Climate analysis v2",
                    "advisory_credibility_notes": {
                        "summary": "This appears to be an unattributed note.",
                        "strengths": ["May contain useful analytical framing."],
                        "weaknesses": ["No identified author or publisher."],
                        "source_reliability_assessment": {
                            "rating": "low",
                            "notes": ["No identified author or publisher."]
                        },
                        "information_credibility_assessment": {
                            "rating": "medium",
                            "notes": ["May contain useful analytical framing."]
                        },
                        "provenance_assessment": {
                            "distance": "secondary",
                            "notes": ["Unverified provenance"]
                        },
                        "risk_flags": ["Unverified provenance"],
                        "recommended_handling": ["Use only as a lead until corroborated."],
                        "verification_steps": ["Locate the original source or publication page."],
                        "citation_advice": "Describe it cautiously as an unattributed note.",
                    },
                }
            ),
            model="gpt-5.4",
            finish_reason="stop",
        )

    assessor = build_llm_credibility_assessor(
        draft_credibility=draft_credibility,
        assessed_at=lambda: datetime(2026, 5, 18, 0, 10, tzinfo=UTC),
    )

    outcome = assessor(
        CredibilityAssessmentRequest(document=document, assessment_method="llm_draft_v1")
    )

    assert outcome.assessment.notes == (
        "Summary: This appears to be an unattributed note.\n"
        "Strengths: May contain useful analytical framing.\n"
        "Concerns: No identified author or publisher.\n"
        "Risk flags: Unverified provenance\n"
        "Recommended handling: Use only as a lead until corroborated.\n"
        "Verification checks: Locate the original source or publication page.\n"
        "Citation advice: Describe it cautiously as an unattributed note."
    )
    assert outcome.assessment.summary == "This appears to be an unattributed note."
    assert outcome.assessment.strengths == ("May contain useful analytical framing.",)
    assert outcome.assessment.concerns == ("No identified author or publisher.",)
    assert outcome.assessment.verification_checks == (
        "Locate the original source or publication page.",
    )
    assert outcome.assessment.source_reliability is CredibilityBand.LOW
    assert outcome.assessment.information_credibility is CredibilityBand.MEDIUM
    assert outcome.assessment.source_reliability_factors == (
        "No identified author or publisher.",
    )
    assert outcome.assessment.information_credibility_factors == (
        "May contain useful analytical framing.",
    )
    assert outcome.assessment.provenance_distance is ProvenanceDistance.SECONDARY


def test_build_llm_credibility_assessor_best_effort_parses_truncated_live_json_blob() -> None:
    document = Document(
        document_id="doc-1",
        case_id="case-1",
        source_type="note",
        source_url=None,
        publisher=None,
        author=None,
        title="Reform briefing note",
        published_at=None,
        retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
        content_hash="sha256:ghi789",
        language="en",
    )

    truncated_blob = '''{
  "document_id": "doc-1",
  "case_id": "case-1",
  "advisory_credibility_notes": {
    "summary": "Credibility is currently indeterminate due to missing provenance and bibliographic metadata.",
    "provenance_assessment": {
      "rating": "low",
      "notes": [
        "Publisher is unknown.",
        "Author is unknown."
      ]
    },
    "risk_flags": [
      "No identifiable publisher or issuing institution.",
      "No named author or responsible organization."
    ],
    "recommended_use": {
      "appropriate_uses": [
        "As a lead for further research.",
        "To extract names, dates, policy terms, or claims to verify elsewhere."
      ],
      "not_recommended_as": [
        "A sole source for factual assertions.",
        "Definitive evidence of institutional position unless independently authenticated."
      ]
    },
    "verification_steps": [
      "Obtain the full document, including cover page, headers, footers, logos,''' 

    def draft_credibility(evidence_summary: str) -> LlmGenerationResult:
        return LlmGenerationResult(
            text=truncated_blob,
            model="gpt-5.4",
            finish_reason="length",
        )

    assessor = build_llm_credibility_assessor(
        draft_credibility=draft_credibility,
        assessed_at=lambda: datetime(2026, 5, 18, 0, 10, tzinfo=UTC),
    )

    outcome = assessor(
        CredibilityAssessmentRequest(document=document, assessment_method="llm_draft_v1")
    )

    assert outcome.assessment.notes == (
        "Summary: Credibility is currently indeterminate due to missing provenance and bibliographic metadata.\n"
        "Concerns: Publisher is unknown.; Author is unknown.\n"
        "Risk flags: No identifiable publisher or issuing institution.; No named author or responsible organization.\n"
        "Recommended handling: As a lead for further research.; To extract names, dates, policy terms, or claims to verify elsewhere.; Not recommended as: A sole source for factual assertions.; Not recommended as: Definitive evidence of institutional position unless independently authenticated."
    )
    assert outcome.assessment.source_reliability is CredibilityBand.UNKNOWN
    assert outcome.assessment.information_credibility is CredibilityBand.UNKNOWN
    assert outcome.assessment.source_reliability_factors == ()
    assert outcome.assessment.information_credibility_factors == ()
    assert outcome.assessment.provenance_distance is ProvenanceDistance.UNKNOWN



def test_build_llm_credibility_assessor_condenses_markdown_prose_into_compact_notes() -> None:
    document = Document(
        document_id="doc-1",
        case_id="case-1",
        source_type="note",
        source_url=None,
        publisher=None,
        author=None,
        title="Reform briefing note",
        published_at=None,
        retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
        content_hash="sha256:ghi789",
        language="en",
    )

    def draft_credibility(evidence_summary: str) -> LlmGenerationResult:
        return LlmGenerationResult(
            text=(
                "**Advisory credibility notes (draft)**\n\n"
                "- **Source transparency is very limited.** No publisher, author, publication date, or source URL is provided, which makes provenance difficult to verify.\n"
                "- **Document type appears informal.** The source is labeled as a **note**, suggesting it may be unpublished, internal, preliminary, or otherwise not subject to editorial review.\n"
                "- **Verification risk is high.** Without identifiable origin details, it is not possible to independently confirm authenticity, context, or whether the document is complete and unaltered.\n"
                "- **Authority cannot be established.** Because the author and publishing entity are unknown, the expertise, institutional affiliation, and potential conflicts of interest cannot be assessed.\n"
                "- **Timeliness is unclear.** The publication date is unknown, so the information may be outdated or lack relevant temporal context.\n"
                "- **Use with caution.** Treat claims from this document as unverified unless corroborated by reliable, attributable sources.\n"
                "- **Recommended handling.** Seek supporting evidence from primary documents, official statements, reputable reporting, or other independently verifiable materials before relying on this source for factual conclusions.\n\n"
                "**Bottom line:**  \n"
                "This document currently has **low standalone credibility** due to missing provenance and attribution metadata. It may still be useful as a lead or contextual note, but it should not be treated as authoritative without external corroboration."
            ),
            model="gpt-5.4",
            finish_reason="stop",
        )

    assessor = build_llm_credibility_assessor(
        draft_credibility=draft_credibility,
        assessed_at=lambda: datetime(2026, 5, 18, 0, 10, tzinfo=UTC),
    )

    outcome = assessor(
        CredibilityAssessmentRequest(document=document, assessment_method="llm_draft_v1")
    )

    assert outcome.assessment.notes == (
        "Summary: This document currently has low standalone credibility due to missing provenance and attribution metadata.\n"
        "Concerns: Source transparency is very limited. No publisher, author, publication date, or source URL is provided, which makes provenance difficult to verify.; Document type appears informal. The source is labeled as a note, suggesting it may be unpublished, internal, preliminary, or otherwise not subject to editorial review.; Verification risk is high. Without identifiable origin details, it is not possible to independently confirm authenticity, context, or whether the document is complete and unaltered.; Authority cannot be established. Because the author and publishing entity are unknown, the expertise, institutional affiliation, and potential conflicts of interest cannot be assessed.; Timeliness is unclear. The publication date is unknown, so the information may be outdated or lack relevant temporal context.\n"
        "Recommended handling: Use with caution. Treat claims from this document as unverified unless corroborated by reliable, attributable sources.; Recommended handling. Seek supporting evidence from primary documents, official statements, reputable reporting, or other independently verifiable materials before relying on this source for factual conclusions."
    )



def test_build_llm_credibility_assessor_maps_primary_source_semantics() -> None:
    document = Document(
        document_id="doc-primary",
        case_id="case-1",
        source_type="press_release",
        source_url="https://example.test/ministry-release",
        publisher="Ministry of Health",
        author=None,
        title="Official release",
        published_at=datetime(2026, 5, 18, 0, 0, tzinfo=UTC),
        retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
        content_hash="sha256:primary123",
        language="en",
    )

    def draft_credibility(evidence_summary: str) -> LlmGenerationResult:
        return LlmGenerationResult(
            text=json.dumps(
                {
                    "summary": "Official primary release with named ministry publisher.",
                    "strengths": ["Named ministry publisher", "Direct publication URL"],
                    "concerns": ["Needs independent confirmation of downstream impact claims"],
                    "verification_checks": ["Confirm quoted figures against annex table"],
                    "source_reliability": "high",
                    "information_credibility": "medium",
                    "source_reliability_factors": ["official_publisher", "primary_release"],
                    "information_credibility_factors": ["impact_claim_needs_confirmation"],
                    "provenance_distance": "primary",
                }
            ),
            model="gpt-5.4",
            finish_reason="stop",
        )

    assessor = build_llm_credibility_assessor(
        draft_credibility=draft_credibility,
        assessed_at=lambda: datetime(2026, 5, 18, 0, 10, tzinfo=UTC),
    )

    outcome = assessor(
        CredibilityAssessmentRequest(document=document, assessment_method="llm_draft_v1")
    )

    assert outcome.assessment.source_reliability is CredibilityBand.HIGH
    assert outcome.assessment.information_credibility is CredibilityBand.MEDIUM
    assert outcome.assessment.source_reliability_factors == (
        "official_publisher",
        "primary_release",
    )
    assert outcome.assessment.information_credibility_factors == (
        "impact_claim_needs_confirmation",
    )
    assert outcome.assessment.provenance_distance is ProvenanceDistance.PRIMARY



def test_build_llm_credibility_assessor_maps_secondary_summary_semantics() -> None:
    document = Document(
        document_id="doc-secondary",
        case_id="case-1",
        source_type="news_article",
        source_url="https://example.test/news-summary",
        publisher="Example News",
        author="Reporter",
        title="Summary of ministry release",
        published_at=datetime(2026, 5, 18, 1, 0, tzinfo=UTC),
        retrieved_at=datetime(2026, 5, 18, 1, 5, tzinfo=UTC),
        content_hash="sha256:secondary123",
        language="en",
    )

    def draft_credibility(evidence_summary: str) -> LlmGenerationResult:
        return LlmGenerationResult(
            text=json.dumps(
                {
                    "summary": "Secondary news write-up of an official release.",
                    "strengths": ["Named reporter", "Named outlet"],
                    "concerns": ["No direct dataset link"],
                    "verification_checks": ["Find linked primary release"],
                    "source_reliability": "medium",
                    "information_credibility": "medium",
                    "source_reliability_factors": ["named_outlet"],
                    "information_credibility_factors": ["secondary_summary", "dataset_not_linked"],
                    "provenance_distance": "secondary",
                }
            ),
            model="gpt-5.4",
            finish_reason="stop",
        )

    assessor = build_llm_credibility_assessor(
        draft_credibility=draft_credibility,
        assessed_at=lambda: datetime(2026, 5, 18, 1, 10, tzinfo=UTC),
    )

    outcome = assessor(
        CredibilityAssessmentRequest(document=document, assessment_method="llm_draft_v1")
    )

    assert outcome.assessment.source_reliability is CredibilityBand.MEDIUM
    assert outcome.assessment.information_credibility is CredibilityBand.MEDIUM
    assert outcome.assessment.source_reliability_factors == ("named_outlet",)
    assert outcome.assessment.information_credibility_factors == (
        "secondary_summary",
        "dataset_not_linked",
    )
    assert outcome.assessment.provenance_distance is ProvenanceDistance.SECONDARY



def test_build_llm_credibility_assessor_maps_unattributed_note_semantics() -> None:
    document = Document(
        document_id="doc-note",
        case_id="case-1",
        source_type="note",
        source_url=None,
        publisher=None,
        author=None,
        title="Unattributed note",
        published_at=None,
        retrieved_at=datetime(2026, 5, 18, 2, 5, tzinfo=UTC),
        content_hash="sha256:note123",
        language="en",
    )

    def draft_credibility(evidence_summary: str) -> LlmGenerationResult:
        return LlmGenerationResult(
            text=json.dumps(
                {
                    "summary": "Unattributed note with weak provenance.",
                    "strengths": ["May provide leads for further checking"],
                    "concerns": ["No publisher", "No author"],
                    "verification_checks": ["Find original publication context"],
                    "source_reliability": "low",
                    "information_credibility": "low",
                    "source_reliability_factors": ["unattributed_note", "no_publisher", "no_author"],
                    "information_credibility_factors": ["claims_unverified"],
                    "provenance_distance": "unknown",
                }
            ),
            model="gpt-5.4",
            finish_reason="stop",
        )

    assessor = build_llm_credibility_assessor(
        draft_credibility=draft_credibility,
        assessed_at=lambda: datetime(2026, 5, 18, 2, 10, tzinfo=UTC),
    )

    outcome = assessor(
        CredibilityAssessmentRequest(document=document, assessment_method="llm_draft_v1")
    )

    assert outcome.assessment.source_reliability is CredibilityBand.LOW
    assert outcome.assessment.information_credibility is CredibilityBand.LOW
    assert outcome.assessment.source_reliability_factors == (
        "unattributed_note",
        "no_publisher",
        "no_author",
    )
    assert outcome.assessment.information_credibility_factors == ("claims_unverified",)
    assert outcome.assessment.provenance_distance is ProvenanceDistance.UNKNOWN



def test_build_llm_credibility_assessor_maps_weak_scraped_snippet_semantics() -> None:
    document = Document(
        document_id="doc-scraped",
        case_id="case-1",
        source_type="scraped_snippet",
        source_url="https://example.test/aggregator-snippet",
        publisher=None,
        author=None,
        title="Aggregator snippet",
        published_at=None,
        retrieved_at=datetime(2026, 5, 18, 3, 5, tzinfo=UTC),
        content_hash="sha256:scraped123",
        language="en",
    )

    def draft_credibility(evidence_summary: str) -> LlmGenerationResult:
        return LlmGenerationResult(
            text=json.dumps(
                {
                    "summary": "Weak scraped snippet with no clear origin.",
                    "strengths": ["Contains searchable phrasing"],
                    "concerns": ["Snippet origin unclear", "Potentially incomplete text"],
                    "verification_checks": ["Locate original source page"],
                    "source_reliability": "low",
                    "information_credibility": "low",
                    "source_reliability_factors": ["weak_scraped_snippet", "origin_unclear"],
                    "information_credibility_factors": ["fragmentary_text", "context_missing"],
                    "provenance_distance": "secondary",
                }
            ),
            model="gpt-5.4",
            finish_reason="stop",
        )

    assessor = build_llm_credibility_assessor(
        draft_credibility=draft_credibility,
        assessed_at=lambda: datetime(2026, 5, 18, 3, 10, tzinfo=UTC),
    )

    outcome = assessor(
        CredibilityAssessmentRequest(document=document, assessment_method="llm_draft_v1")
    )

    assert outcome.assessment.source_reliability is CredibilityBand.LOW
    assert outcome.assessment.information_credibility is CredibilityBand.LOW
    assert outcome.assessment.source_reliability_factors == (
        "weak_scraped_snippet",
        "origin_unclear",
    )
    assert outcome.assessment.information_credibility_factors == (
        "fragmentary_text",
        "context_missing",
    )
    assert outcome.assessment.provenance_distance is ProvenanceDistance.SECONDARY



def test_build_llm_credibility_assessor_includes_prepared_text_in_prompt() -> None:
    document = Document(
        document_id="doc-1",
        case_id="case-1",
        source_type="inline_text",
        source_url=None,
        publisher=None,
        author=None,
        title="Apollo note",
        published_at=None,
        retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
        content_hash="sha256:abc123",
        language="en",
    )
    prompts: list[str] = []

    def draft_credibility(evidence_summary: str) -> LlmGenerationResult:
        prompts.append(evidence_summary)
        return LlmGenerationResult(
            text='{"summary":"Uses provided text."}',
            model="gpt-5.4",
            finish_reason="stop",
        )

    assessor = build_llm_credibility_assessor(
        draft_credibility=draft_credibility,
        assessed_at=lambda: datetime(2026, 5, 18, 0, 10, tzinfo=UTC),
    )

    outcome = assessor(
        CredibilityAssessmentRequest(
            document=document,
            assessment_method="llm_draft_v1",
            prepared_chunks=(
                DocumentChunk(
                    chunk_id="doc-1:chunk-1",
                    case_id="case-1",
                    document_id="doc-1",
                    raw_text="Apollo 11 landed on the Moon in 1969.",
                    start_char=0,
                    end_char=38,
                    chunk_index=0,
                ),
            ),
        )
    )

    assert "Prepared source text excerpt:" in prompts[0]
    assert "Apollo 11 landed on the Moon in 1969." in prompts[0]
    assert "No prepared source text was provided." not in prompts[0]
    assert "Required top-level keys: summary, strengths, concerns, verification_checks, source_reliability, information_credibility, source_reliability_factors, information_credibility_factors, provenance_distance." in prompts[0]
    assert "Allowed values: source_reliability/information_credibility = high|medium|low|unknown; provenance_distance = primary|near_primary|secondary|unknown." in prompts[0]
    assert "Treat unattributed notes, anonymous reposts, and weak scraped snippets as low source_reliability unless the text itself supplies strong provenance." in prompts[0]
    assert "Treat secondary news summaries as secondary provenance unless they clearly embed or link the original primary material." in prompts[0]
    assert "Use primary provenance only when the document is itself the original release, filing, transcript, or first-party publication." in prompts[0]
    assert "Return valid JSON with double-quoted keys and no markdown fences." in prompts[0]
    assert outcome.assessment.notes == "Summary: Uses provided text."



def test_build_llm_runtime_credibility_draft_gateway_can_drive_application_assessment_callable() -> None:
    config = SourceTraceLlmConfig(
        bootstrap=LlmBootstrapConfig(
            api_key_env_var="SOURCETRACE_LLM_API_KEY",
            base_url_env_var="SOURCETRACE_LLM_BASE_URL",
        ),
        profiles={
            "fast_extract": LlmProfileConfig(model="gpt-4o-mini", temperature=0.0),
            "reasoning": LlmProfileConfig(model="gpt-4.1-mini", temperature=0.2),
        },
        tasks={
            "claim_extraction": LlmTaskConfig(profile="fast_extract"),
            "credibility_draft": LlmTaskConfig(profile="reasoning"),
        },
    )
    document = Document(
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
    original_api_key = environ.get("SOURCETRACE_LLM_API_KEY")
    original_base_url = environ.get("SOURCETRACE_LLM_BASE_URL")

    def completion_fn(**kwargs: object) -> dict[str, object]:
        if kwargs.get("response_format") == {"type": "json_object"}:
            return {
                "model": kwargs["model"],
                "choices": [
                    {
                        "message": {"parsed": {"claims": []}},
                        "finish_reason": "stop",
                    }
                ],
            }
        return {
            "model": kwargs["model"],
            "choices": [
                {
                    "message": {"content": "Corroborated by two independent reports."},
                    "finish_reason": "stop",
                }
            ],
        }

    try:
        environ["SOURCETRACE_LLM_API_KEY"] = "test-api-key"
        environ["SOURCETRACE_LLM_BASE_URL"] = "https://llm.example.test"
        runtime = build_llm_runtime(completion_fn=completion_fn, config=config)

        def assess_credibility(
            request: CredibilityAssessmentRequest,
        ) -> CredibilityAssessmentOutcome:
            draft = runtime.credibility_draft(
                f"Assess credibility for document {request.document.document_id}."
            )
            assessment = DocumentCredibilityAssessment(
                assessment_id="cred-1",
                document_id=request.document.document_id,
                source_reliability=CredibilityBand.MEDIUM,
                information_credibility=CredibilityBand.MEDIUM,
                source_reliability_factors=("publisher_history",),
                information_credibility_factors=("partial_corroboration",),
                provenance_distance=ProvenanceDistance.NEAR_PRIMARY,
                method=request.assessment_method or "llm_draft_v1",
                notes=draft.text,
                assessed_by="system",
                assessed_at=datetime(2026, 5, 18, 0, 10, tzinfo=UTC),
                override=False,
            )
            return CredibilityAssessmentOutcome(request=request, assessment=assessment)

        execution = CredibilityAssessmentExecution(assess_credibility=assess_credibility)
        outcome = execution.assess_credibility(
            CredibilityAssessmentRequest(
                document=document,
                assessment_method="llm_draft_v1",
            )
        )

        assert outcome.request.document is document
        assert outcome.assessment.document_id == document.document_id
        assert outcome.assessment.method == "llm_draft_v1"
        assert outcome.assessment.notes == "Corroborated by two independent reports."
    finally:
        if original_api_key is None:
            environ.pop("SOURCETRACE_LLM_API_KEY", None)
        else:
            environ["SOURCETRACE_LLM_API_KEY"] = original_api_key

        if original_base_url is None:
            environ.pop("SOURCETRACE_LLM_BASE_URL", None)
        else:
            environ["SOURCETRACE_LLM_BASE_URL"] = original_base_url
