"""Minimal application runtime for LLM-backed credibility assessment."""

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, TypedDict

from sourcetrace.application.credibility import (
    CredibilityAssessmentOutcome,
    CredibilityAssessmentRequest,
)
from sourcetrace.domain import DocumentCredibilityAssessment
from sourcetrace.domain.types import CredibilityBand, ProvenanceDistance

if TYPE_CHECKING:
    from sourcetrace.llm.interfaces import CredibilityDraftGateway


class StructuredCredibilityNotes(TypedDict):
    notes: str | None
    summary: str | None
    strengths: tuple[str, ...]
    concerns: tuple[str, ...]
    verification_checks: tuple[str, ...]
    source_reliability: CredibilityBand
    information_credibility: CredibilityBand
    source_reliability_factors: tuple[str, ...]
    information_credibility_factors: tuple[str, ...]
    provenance_distance: ProvenanceDistance


class _LlmCredibilityAssessor:
    def __init__(
        self,
        *,
        draft_credibility: "CredibilityDraftGateway",
        assessed_at: Callable[[], datetime],
        assessed_by: str,
    ) -> None:
        self._draft_credibility = draft_credibility
        self._assessed_at = assessed_at
        self._assessed_by = assessed_by

    def __call__(
        self,
        request: CredibilityAssessmentRequest,
    ) -> CredibilityAssessmentOutcome:
        document = request.document
        draft = self._draft_credibility(_credibility_prompt(request))
        structured = _structured_credibility_notes(draft.text)
        assessment = DocumentCredibilityAssessment(
            assessment_id=f"credibility-{document.document_id}",
            document_id=document.document_id,
            source_reliability=structured["source_reliability"],
            information_credibility=structured["information_credibility"],
            source_reliability_factors=structured["source_reliability_factors"],
            information_credibility_factors=structured["information_credibility_factors"],
            provenance_distance=structured["provenance_distance"],
            method=request.assessment_method or "llm_draft_v1",
            notes=structured["notes"],
            summary=structured["summary"],
            strengths=structured["strengths"],
            concerns=structured["concerns"],
            verification_checks=structured["verification_checks"],
            assessed_by=self._assessed_by,
            assessed_at=self._assessed_at(),
            override=False,
        )
        return CredibilityAssessmentOutcome(request=request, assessment=assessment)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _normalize_credibility_notes(text: str) -> str | None:
    return _structured_credibility_notes(text)["notes"]


def _structured_credibility_notes(text: str) -> StructuredCredibilityNotes:
    normalized = text.strip()
    empty: StructuredCredibilityNotes = {
        "notes": None,
        "summary": None,
        "strengths": (),
        "concerns": (),
        "verification_checks": (),
        "source_reliability": CredibilityBand.UNKNOWN,
        "information_credibility": CredibilityBand.UNKNOWN,
        "source_reliability_factors": (),
        "information_credibility_factors": (),
        "provenance_distance": ProvenanceDistance.UNKNOWN,
    }
    if not normalized:
        return empty
    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError:
        structured = _best_effort_structured_credibility_notes(normalized)
        if structured["notes"] is None:
            return {
                **empty,
                "notes": normalized,
            }
        return structured
    if not isinstance(payload, dict):
        return {
            **empty,
            "notes": normalized,
        }

    rendered = _render_credibility_payload(payload)
    if rendered["notes"] is None:
        return {
            **empty,
            "notes": normalized,
        }
    return rendered


def _string_or_none(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    items = []
    for item in value:
        if not isinstance(item, str):
            continue
        normalized = item.strip()
        if normalized:
            items.append(normalized)
    return tuple(items)


def _first_nonempty_string_list(payload: dict[str, object], *keys: str) -> tuple[str, ...]:
    for key in keys:
        items = _string_list(payload.get(key))
        if items:
            return items
    return ()


def _render_credibility_payload(payload: dict[str, object]) -> StructuredCredibilityNotes:
    advisory_payload = payload.get("advisory_credibility_notes")
    if isinstance(advisory_payload, dict):
        payload = advisory_payload

    summary = _string_or_none(payload.get("summary"))
    strengths = _first_nonempty_string_list(payload, "strengths")
    concerns = _first_nonempty_string_list(payload, "concerns", "weaknesses")
    if not concerns:
        provenance = payload.get("provenance_assessment")
        if isinstance(provenance, dict):
            concerns = _string_list(provenance.get("notes"))

    verification_checks = _first_nonempty_string_list(
        payload,
        "verification_checks",
        "verification_steps",
    )
    source_reliability = _credibility_band_from_payload(
        payload,
        "source_reliability",
        "source_reliability_band",
        nested=("source_reliability_assessment", "rating"),
    )
    information_credibility = _credibility_band_from_payload(
        payload,
        "information_credibility",
        "information_credibility_band",
        nested=("information_credibility_assessment", "rating"),
    )
    provenance_distance = _provenance_distance_from_payload(payload)
    source_reliability_factors = _first_nonempty_string_list(
        payload,
        "source_reliability_factors",
        "source_strengths",
    )
    if not source_reliability_factors:
        source_reliability_factors = _nested_notes_tuple(
            payload,
            "source_reliability_assessment",
        )
    information_credibility_factors = _first_nonempty_string_list(
        payload,
        "information_credibility_factors",
        "information_strengths",
    )
    if not information_credibility_factors:
        information_credibility_factors = _nested_notes_tuple(
            payload,
            "information_credibility_assessment",
        )

    lines: list[str] = []
    if summary is not None:
        lines.append(f"Summary: {summary}")
    if strengths:
        lines.append(f"Strengths: {'; '.join(strengths)}")
    if concerns:
        lines.append(f"Concerns: {'; '.join(concerns)}")

    risk_flags = _first_nonempty_string_list(payload, "risk_flags")
    if risk_flags:
        lines.append(f"Risk flags: {'; '.join(risk_flags)}")

    recommended_handling = _first_nonempty_string_list(payload, "recommended_handling")
    if not recommended_handling:
        recommended_use = payload.get("recommended_use")
        if isinstance(recommended_use, dict):
            recommended_handling = _string_list(recommended_use.get("appropriate_uses"))
            not_recommended = _string_list(recommended_use.get("not_recommended_as"))
            if not_recommended:
                recommended_handling = recommended_handling + tuple(
                    f"Not recommended as: {item}" for item in not_recommended
                )
    if recommended_handling:
        lines.append(f"Recommended handling: {'; '.join(recommended_handling)}")

    if verification_checks:
        lines.append(f"Verification checks: {'; '.join(verification_checks)}")

    citation_advice = _string_or_none(payload.get("citation_advice"))
    if citation_advice is not None:
        lines.append(f"Citation advice: {citation_advice}")

    return {
        "notes": "\n".join(lines) if lines else None,
        "summary": summary,
        "strengths": strengths,
        "concerns": concerns,
        "verification_checks": verification_checks,
        "source_reliability": source_reliability,
        "information_credibility": information_credibility,
        "source_reliability_factors": source_reliability_factors,
        "information_credibility_factors": information_credibility_factors,
        "provenance_distance": provenance_distance,
    }


def _best_effort_credibility_notes(text: str) -> str | None:
    return _best_effort_structured_credibility_notes(text)["notes"]


def _best_effort_structured_credibility_notes(text: str) -> StructuredCredibilityNotes:
    lines: list[str] = []

    summary = _extract_first_string_field(text, "summary")
    if summary is None:
        summary = _extract_markdown_bottom_line(text)
    if summary is not None:
        lines.append(f"Summary: {summary}")

    strengths = _extract_string_list(text, "strengths")
    if strengths:
        lines.append(f"Strengths: {'; '.join(strengths)}")

    concerns = _extract_string_list(text, "concerns") or _extract_string_list(text, "weaknesses")
    if not concerns:
        concerns = _extract_nested_string_list(text, "provenance_assessment", "notes")
    if not concerns:
        concerns = _extract_markdown_bullets(
            text,
            headings=(
                "Source transparency is very limited",
                "Document type appears informal",
                "Verification risk is high",
                "Authority cannot be established",
                "Timeliness is unclear",
            ),
        )
    if concerns:
        lines.append(f"Concerns: {'; '.join(concerns)}")

    risk_flags = _extract_string_list(text, "risk_flags")
    if risk_flags:
        lines.append(f"Risk flags: {'; '.join(risk_flags)}")

    recommended_handling = _extract_string_list(text, "recommended_handling")
    if not recommended_handling:
        recommended_handling = _extract_nested_string_list(text, "recommended_use", "appropriate_uses")
        not_recommended = _extract_nested_string_list(text, "recommended_use", "not_recommended_as")
        if not_recommended:
            recommended_handling = recommended_handling + tuple(
                f"Not recommended as: {item}" for item in not_recommended
            )
    if not recommended_handling:
        recommended_handling = _extract_markdown_bullets(
            text,
            headings=("Recommended handling", "Use with caution"),
        )
    if recommended_handling:
        lines.append(f"Recommended handling: {'; '.join(recommended_handling)}")

    verification_checks = _extract_string_list(text, "verification_checks")
    if not verification_checks:
        verification_checks = _extract_string_list(text, "verification_steps")
    if verification_checks:
        lines.append(f"Verification checks: {'; '.join(verification_checks)}")

    citation_advice = _extract_first_string_field(text, "citation_advice")
    if citation_advice is not None:
        lines.append(f"Citation advice: {citation_advice}")

    source_reliability = _credibility_band_from_text(
        text,
        field_names=("source_reliability", "source_reliability_band"),
        nested_name="source_reliability_assessment",
    )
    information_credibility = _credibility_band_from_text(
        text,
        field_names=("information_credibility", "information_credibility_band"),
        nested_name="information_credibility_assessment",
    )
    provenance_distance = _provenance_distance_from_text(text)
    source_reliability_factors = _extract_string_list(text, "source_reliability_factors")
    if not source_reliability_factors:
        source_reliability_factors = _extract_nested_string_list(
            text,
            "source_reliability_assessment",
            "notes",
        )
    information_credibility_factors = _extract_string_list(
        text,
        "information_credibility_factors",
    )
    if not information_credibility_factors:
        information_credibility_factors = _extract_nested_string_list(
            text,
            "information_credibility_assessment",
            "notes",
        )

    return {
        "notes": "\n".join(lines) if lines else None,
        "summary": summary,
        "strengths": strengths,
        "concerns": concerns,
        "verification_checks": verification_checks,
        "source_reliability": source_reliability,
        "information_credibility": information_credibility,
        "source_reliability_factors": source_reliability_factors,
        "information_credibility_factors": information_credibility_factors,
        "provenance_distance": provenance_distance,
    }


def _extract_first_string_field(text: str, field_name: str) -> str | None:
    pattern = re.compile(rf'"{re.escape(field_name)}"\s*:\s*"((?:\\.|[^"\\])*)"')
    match = pattern.search(text)
    if match is None:
        return None
    return _decode_json_string_fragment(match.group(1))


def _extract_string_list(text: str, field_name: str) -> tuple[str, ...]:
    pattern = re.compile(rf'"{re.escape(field_name)}"\s*:\s*\[(.*?)\]', re.DOTALL)
    match = pattern.search(text)
    if match is None:
        return ()
    return _extract_all_strings(match.group(1))


def _extract_nested_string_list(text: str, object_name: str, field_name: str) -> tuple[str, ...]:
    object_pattern = re.compile(rf'"{re.escape(object_name)}"\s*:\s*\{{(.*?)\n\s*\}}', re.DOTALL)
    match = object_pattern.search(text)
    if match is None:
        return ()
    return _extract_string_list(match.group(1), field_name)


def _extract_markdown_bullets(text: str, headings: tuple[str, ...]) -> tuple[str, ...]:
    items: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("-"):
            continue
        content = line[1:].strip()
        if not content:
            continue
        normalized = re.sub(r"\*\*([^*]+)\*\*", r"\1", content)
        for heading in headings:
            if normalized.lower().startswith(heading.lower()):
                items.append(normalized)
                break
    return tuple(items)


def _extract_markdown_bottom_line(text: str) -> str | None:
    pattern = re.compile(r"\*\*Bottom line:\*\*\s*(.+)", re.IGNORECASE | re.DOTALL)
    match = pattern.search(text)
    if match is None:
        return None
    normalized = re.sub(r"\*\*([^*]+)\*\*", r"\1", match.group(1))
    normalized = re.sub(r"\s+", " ", normalized).strip()
    sentence_match = re.match(r"(.+?[.!?])(?:\s|$)", normalized)
    if sentence_match is not None:
        normalized = sentence_match.group(1).strip()
    return normalized or None


def _extract_all_strings(fragment: str) -> tuple[str, ...]:
    pattern = re.compile(r'"((?:\\.|[^"\\])*)"')
    return tuple(
        decoded
        for raw in pattern.findall(fragment)
        if (decoded := _decode_json_string_fragment(raw)) is not None
    )


def _credibility_band_from_payload(
    payload: dict[str, object],
    *field_names: str,
    nested: tuple[str, str] | None = None,
) -> CredibilityBand:
    candidates: list[str] = []
    for field_name in field_names:
        value = _string_or_none(payload.get(field_name))
        if value is not None:
            candidates.append(value)
    if nested is not None:
        nested_object = payload.get(nested[0])
        if isinstance(nested_object, dict):
            nested_value = _string_or_none(nested_object.get(nested[1]))
            if nested_value is not None:
                candidates.append(nested_value)
    return _credibility_band_from_candidates(candidates)


def _credibility_band_from_text(
    text: str,
    *,
    field_names: tuple[str, ...],
    nested_name: str | None = None,
) -> CredibilityBand:
    candidates: list[str] = []
    for field_name in field_names:
        value = _extract_first_string_field(text, field_name)
        if value is not None:
            candidates.append(value)
    if nested_name is not None:
        nested_rating = _extract_nested_first_string_field(text, nested_name, "rating")
        if nested_rating is not None:
            candidates.append(nested_rating)
    return _credibility_band_from_candidates(candidates)


def _credibility_band_from_candidates(candidates: list[str]) -> CredibilityBand:
    normalized = [item.strip().casefold().replace("-", "_").replace(" ", "_") for item in candidates]
    if any(item in {"high", "strong", "reliable"} for item in normalized):
        return CredibilityBand.HIGH
    if any(item in {"medium", "moderate", "mixed"} for item in normalized):
        return CredibilityBand.MEDIUM
    if any(item in {"low", "weak", "limited", "poor"} for item in normalized):
        return CredibilityBand.LOW
    return CredibilityBand.UNKNOWN


def _provenance_distance_from_payload(payload: dict[str, object]) -> ProvenanceDistance:
    candidates: list[str] = []
    for field_name in ("provenance_distance", "provenance"):
        value = _string_or_none(payload.get(field_name))
        if value is not None:
            candidates.append(value)
    nested_object = payload.get("provenance_assessment")
    if isinstance(nested_object, dict):
        for nested_name in ("distance", "provenance_distance", "rating"):
            value = _string_or_none(nested_object.get(nested_name))
            if value is not None:
                candidates.append(value)
    return _provenance_distance_from_candidates(candidates)


def _provenance_distance_from_text(text: str) -> ProvenanceDistance:
    candidates: list[str] = []
    for field_name in ("provenance_distance", "provenance"):
        value = _extract_first_string_field(text, field_name)
        if value is not None:
            candidates.append(value)
    for nested_name in ("distance", "provenance_distance", "rating"):
        value = _extract_nested_first_string_field(text, "provenance_assessment", nested_name)
        if value is not None:
            candidates.append(value)
    return _provenance_distance_from_candidates(candidates)


def _provenance_distance_from_candidates(candidates: list[str]) -> ProvenanceDistance:
    normalized = [item.strip().casefold().replace("-", "_").replace(" ", "_") for item in candidates]
    if any(item in {"primary", "direct", "original"} for item in normalized):
        return ProvenanceDistance.PRIMARY
    if any(item in {"near_primary", "near-primary", "close_to_primary"} for item in normalized):
        return ProvenanceDistance.NEAR_PRIMARY
    if any(item in {"secondary", "indirect", "reported"} for item in normalized):
        return ProvenanceDistance.SECONDARY
    return ProvenanceDistance.UNKNOWN


def _nested_notes_tuple(payload: dict[str, object], key: str) -> tuple[str, ...]:
    nested = payload.get(key)
    if not isinstance(nested, dict):
        return ()
    return _string_list(nested.get("notes"))


def _extract_nested_first_string_field(text: str, object_name: str, field_name: str) -> str | None:
    object_pattern = re.compile(rf'"{re.escape(object_name)}"\s*:\s*\{{(.*?)\n\s*\}}', re.DOTALL)
    match = object_pattern.search(text)
    if match is None:
        return None
    return _extract_first_string_field(match.group(1), field_name)


def _decode_json_string_fragment(value: str) -> str | None:
    try:
        decoded = json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return None
    normalized = decoded.strip()
    return normalized or None


def _credibility_prompt(request: CredibilityAssessmentRequest) -> str:
    document = request.document
    lines = [
        "Draft advisory credibility notes for this source document.",
        f"Document ID: {document.document_id}",
        f"Case ID: {document.case_id}",
        f"Source type: {document.source_type}",
        f"Source URL: {document.source_url or 'unknown'}",
        f"Publisher: {document.publisher or 'unknown'}",
        f"Author: {document.author or 'unknown'}",
        f"Title: {document.title or 'unknown'}",
        "Published at: "
        f"{document.published_at.isoformat() if document.published_at else 'unknown'}",
        f"Retrieved at: {document.retrieved_at.isoformat()}",
        f"Language: {document.language or 'unknown'}",
        f"Requested method: {request.assessment_method or 'llm_draft_v1'}",
        "Prepared source text excerpt:",
        _prepared_text_excerpt(request.prepared_chunks) or "No prepared source text was provided.",
        "Respond as concise JSON only.",
        "Required top-level keys: summary, strengths, concerns, verification_checks, source_reliability, information_credibility, source_reliability_factors, information_credibility_factors, provenance_distance.",
        "Allowed values: source_reliability/information_credibility = high|medium|low|unknown; provenance_distance = primary|near_primary|secondary|unknown.",
        "If evidence is missing or ambiguous, explicitly return unknown instead of guessing.",
        "Treat unattributed notes, anonymous reposts, and weak scraped snippets as low source_reliability unless the text itself supplies strong provenance.",
        "Treat secondary news summaries as secondary provenance unless they clearly embed or link the original primary material.",
        "Use primary provenance only when the document is itself the original release, filing, transcript, or first-party publication.",
        "Keep strengths/concerns/factor fields as short string arrays, not paragraphs.",
        "Return valid JSON with double-quoted keys and no markdown fences.",
        "If prepared source text is available, assess both metadata limitations and what the actual text suggests about specificity, attribution, and verification needs.",
    ]
    return "\n".join(lines)



def _prepared_text_excerpt(chunks: tuple[object, ...]) -> str | None:
    excerpts: list[str] = []
    for chunk in chunks[:3]:
        raw_text = getattr(chunk, "raw_text", None)
        if not isinstance(raw_text, str):
            continue
        normalized = raw_text.strip()
        if normalized:
            excerpts.append(normalized)
    if not excerpts:
        return None
    return "\n---\n".join(excerpts)


def build_llm_credibility_assessor(
    *,
    draft_credibility: "CredibilityDraftGateway",
    assessed_at: Callable[[], datetime] | None = None,
    assessed_by: str = "system",
) -> _LlmCredibilityAssessor:
    """Bind the LLM credibility draft gateway into the application assessment shape."""

    return _LlmCredibilityAssessor(
        draft_credibility=draft_credibility,
        assessed_at=assessed_at or _utc_now,
        assessed_by=assessed_by,
    )


__all__ = ["build_llm_credibility_assessor"]
