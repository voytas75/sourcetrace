"""Minimal application runtime for LLM-backed credibility assessment."""

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sourcetrace.application.credibility import (
    CredibilityAssessmentOutcome,
    CredibilityAssessmentRequest,
)
from sourcetrace.domain import DocumentCredibilityAssessment
from sourcetrace.domain.types import CredibilityBand, ProvenanceDistance

if TYPE_CHECKING:
    from sourcetrace.llm.interfaces import CredibilityDraftGateway


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
        assessment = DocumentCredibilityAssessment(
            assessment_id=f"credibility-{document.document_id}",
            document_id=document.document_id,
            source_reliability=CredibilityBand.UNKNOWN,
            information_credibility=CredibilityBand.UNKNOWN,
            source_reliability_factors=(),
            information_credibility_factors=(),
            provenance_distance=ProvenanceDistance.UNKNOWN,
            method=request.assessment_method or "llm_draft_v1",
            notes=_normalize_credibility_notes(draft.text),
            assessed_by=self._assessed_by,
            assessed_at=self._assessed_at(),
            override=False,
        )
        return CredibilityAssessmentOutcome(request=request, assessment=assessment)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _normalize_credibility_notes(text: str) -> str | None:
    normalized = text.strip()
    if not normalized:
        return None
    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError:
        best_effort = _best_effort_credibility_notes(normalized)
        return best_effort or normalized
    if not isinstance(payload, dict):
        return normalized

    rendered = _render_credibility_payload(payload)
    return rendered or normalized


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


def _render_credibility_payload(payload: dict[str, object]) -> str | None:
    advisory_payload = payload.get("advisory_credibility_notes")
    if isinstance(advisory_payload, dict):
        payload = advisory_payload

    lines: list[str] = []
    summary = _string_or_none(payload.get("summary"))
    if summary is not None:
        lines.append(f"Summary: {summary}")

    strengths = _first_nonempty_string_list(payload, "strengths")
    if strengths:
        lines.append(f"Strengths: {'; '.join(strengths)}")

    concerns = _first_nonempty_string_list(payload, "concerns", "weaknesses")
    if concerns:
        lines.append(f"Concerns: {'; '.join(concerns)}")
    else:
        provenance = payload.get("provenance_assessment")
        if isinstance(provenance, dict):
            provenance_notes = _string_list(provenance.get("notes"))
            if provenance_notes:
                lines.append(f"Concerns: {'; '.join(provenance_notes)}")

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

    verification_checks = _first_nonempty_string_list(
        payload,
        "verification_checks",
        "verification_steps",
    )
    if verification_checks:
        lines.append(f"Verification checks: {'; '.join(verification_checks)}")

    citation_advice = _string_or_none(payload.get("citation_advice"))
    if citation_advice is not None:
        lines.append(f"Citation advice: {citation_advice}")
    return "\n".join(lines) if lines else None


def _best_effort_credibility_notes(text: str) -> str | None:
    lines: list[str] = []

    summary = _extract_first_string_field(text, "summary")
    if summary is None:
        summary = _extract_markdown_bottom_line(text)
    if summary is not None:
        lines.append(f"Summary: {summary}")

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

    return "\n".join(lines) if lines else None


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
    ]
    return "\n".join(lines)


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
