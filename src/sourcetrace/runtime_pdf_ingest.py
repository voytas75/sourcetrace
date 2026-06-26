from __future__ import annotations

from typing import Any, Protocol

from sourcetrace.application import PdfIngestResult


class RuntimePdfCapability(Protocol):
    """Runtime-provided PDF analysis capability returning parsed JSON dictionaries."""

    def __call__(self, *, pdf: str, prompt: str, pages: str = "") -> dict[str, Any]:
        ...


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    return max(0.0, min(1.0, parsed))


def _coerce_positive_ints(values: Any, limit: int) -> list[int]:
    if not isinstance(values, list):
        return []
    out: list[int] = []
    for item in values:
        try:
            page = int(item)
        except Exception:
            continue
        if page > 0:
            out.append(page)
    return out[:limit]


def _coerce_strings(values: Any, limit: int) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for item in values:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out[:limit]


def parse_preview_relevance(preview_json: dict[str, Any]) -> str:
    value = str(preview_json.get("relevance_verdict", "irrelevant") or "").strip().lower()
    if value in {"relevant", "uncertain", "irrelevant"}:
        return value
    return "irrelevant"


def parse_preview_scope(preview_json: dict[str, Any]) -> str:
    return str(preview_json.get("document_scope", "") or "").strip()


def parse_preview_entity_match(preview_json: dict[str, Any]) -> str:
    return str(preview_json.get("main_entity", "") or "").strip()


def parse_preview_confidence(preview_json: dict[str, Any]) -> float:
    return _coerce_float(preview_json.get("confidence", 0.0), default=0.0)


def parse_preview_candidate_pages(preview_json: dict[str, Any]) -> list[int]:
    return _coerce_positive_ints(preview_json.get("candidate_pages") or [], limit=8)


def parse_full_relevant(full_json: dict[str, Any]) -> bool:
    return bool(full_json.get("relevant", False))


def parse_full_scope(full_json: dict[str, Any]) -> str:
    return str(full_json.get("document_scope", "") or "").strip()


def parse_full_entity_match(full_json: dict[str, Any]) -> str:
    return str(full_json.get("entity_match_summary", "") or "").strip()


def parse_full_key_findings(full_json: dict[str, Any]) -> list[str]:
    return _coerce_strings(full_json.get("key_findings") or [], limit=5)


def parse_full_evidence_pages(full_json: dict[str, Any]) -> list[int]:
    return _coerce_positive_ints(full_json.get("evidence_pages") or [], limit=5)


def parse_full_confidence(full_json: dict[str, Any]) -> float:
    return _coerce_float(full_json.get("confidence", 0.0), default=0.0)


def _preview_prompt(*, query: str, title: str) -> str:
    return f"""
Read only page 1 of this PDF.

Query: {query}
Title hint: {title}

Return JSON only with this exact schema:
{{
  "document_title": "string",
  "main_entity": "string",
  "document_scope": "string",
  "relevance_verdict": "relevant|uncertain|irrelevant",
  "reason": "string",
  "candidate_pages": [1],
  "confidence": 0.0
}}
""".strip()


def _candidate_page_selection_prompt(*, query: str, title: str, preview_scope: str, preview_entity: str, candidate_pages: list[int]) -> str:
    pages_hint = ', '.join(str(page) for page in candidate_pages[:8]) if candidate_pages else 'none'
    return f"""
You are selecting the most useful PDF pages for a user research query.

User query: {query}
Title hint: {title}
Preview scope: {preview_scope}
Preview entity match: {preview_entity}
Preview candidate pages: {pages_hint}

Choose pages most likely to contain substantive findings relevant to the user query.
Prefer pages with sections like findings, results, ustalenia, ocena, wnioski, zalecenia, recommendations, conclusions, or direct subject-specific discussion.
Avoid boilerplate, cover pages, signatures, legal footer pages, and generic institutional introductions unless they are the only useful context.

Return JSON only with this exact schema:
{{
  "selected_pages": [1],
  "reason": "string",
  "confidence": 0.0
}}
""".strip()


def _full_prompt(*, query: str, title: str) -> str:
    return f"""
Analyze this PDF for the query: {query}

Title hint: {title}

Return JSON only with this exact schema:
{{
  "relevant": true,
  "document_scope": "string",
  "entity_match_summary": "string",
  "key_findings": ["string"],
  "evidence_pages": [1],
  "confidence": 0.0
}}
""".strip()


def _select_pages_with_llm_heuristic(*, pdf_capability: RuntimePdfCapability, pdf: str, query: str, title: str, preview_scope: str, preview_entity: str, candidate_pages: list[int]) -> list[int]:
    if not candidate_pages:
        return []
    try:
        selection = pdf_capability(
            pdf=pdf,
            pages=','.join(str(page) for page in candidate_pages[:8]),
            prompt=_candidate_page_selection_prompt(
                query=query,
                title=title,
                preview_scope=preview_scope,
                preview_entity=preview_entity,
                candidate_pages=candidate_pages,
            ),
        )
    except Exception:
        return candidate_pages[:8]
    if not isinstance(selection, dict):
        return candidate_pages[:8]
    selected_pages = _coerce_positive_ints(selection.get('selected_pages') or [], limit=8)
    return selected_pages or candidate_pages[:8]


def build_research_pdf_analyzer(pdf_capability: RuntimePdfCapability):
    """Build a SourceTrace-compatible PDF ingest callback backed by a runtime PDF capability."""

    def research_pdf_analyzer(
        *,
        query: str,
        url: str,
        title: str,
        triage_verdict: str,
    ) -> PdfIngestResult:
        if triage_verdict not in {"relevant", "uncertain"}:
            return PdfIngestResult(
                relevant=False,
                confidence=0.0,
                document_scope="triage_blocked",
                entity_match_summary="Skipped because triage verdict was not positive.",
                key_findings=(),
                evidence_pages=(),
            )

        try:
            preview = pdf_capability(
                pdf=url,
                pages="1",
                prompt=_preview_prompt(query=query, title=title),
            )
        except Exception as exc:
            return PdfIngestResult(
                relevant=False,
                confidence=0.0,
                document_scope="preview_failed",
                entity_match_summary=f"Preview read failed: {type(exc).__name__}",
                key_findings=(),
                evidence_pages=(),
            )

        if not isinstance(preview, dict):
            return PdfIngestResult(
                relevant=False,
                confidence=0.0,
                document_scope="preview_invalid",
                entity_match_summary="Preview did not return valid JSON.",
                key_findings=(),
                evidence_pages=(),
            )

        preview_relevance = parse_preview_relevance(preview)
        preview_scope = parse_preview_scope(preview)
        preview_entity = parse_preview_entity_match(preview)
        preview_confidence = parse_preview_confidence(preview)
        candidate_pages = parse_preview_candidate_pages(preview)

        if preview_relevance == "irrelevant":
            return PdfIngestResult(
                relevant=False,
                confidence=preview_confidence or 0.7,
                document_scope=preview_scope or "preview_only",
                entity_match_summary=preview_entity or "No clear subject match on preview.",
                key_findings=(),
                evidence_pages=tuple(candidate_pages[:5]),
            )

        selected_pages = _select_pages_with_llm_heuristic(
            pdf_capability=pdf_capability,
            pdf=url,
            query=query,
            title=title,
            preview_scope=preview_scope,
            preview_entity=preview_entity,
            candidate_pages=candidate_pages,
        )
        full_pages = ",".join(str(page) for page in selected_pages[:8]) if selected_pages else ""

        try:
            full = pdf_capability(
                pdf=url,
                pages=full_pages,
                prompt=_full_prompt(query=query, title=title),
            )
        except Exception as exc:
            return PdfIngestResult(
                relevant=False,
                confidence=preview_confidence or 0.4,
                document_scope=preview_scope or "full_read_failed",
                entity_match_summary=f"Full read failed after positive preview: {type(exc).__name__}",
                key_findings=(),
                evidence_pages=tuple(selected_pages[:5] or candidate_pages[:5]),
            )

        if not isinstance(full, dict):
            return PdfIngestResult(
                relevant=False,
                confidence=preview_confidence or 0.4,
                document_scope=preview_scope or "full_invalid",
                entity_match_summary=preview_entity or "Full read did not return valid JSON.",
                key_findings=(),
                evidence_pages=tuple(selected_pages[:5] or candidate_pages[:5]),
            )

        full_relevant = parse_full_relevant(full)
        full_scope = parse_full_scope(full)
        full_entity = parse_full_entity_match(full)
        full_key_findings = parse_full_key_findings(full)
        full_pages_found = parse_full_evidence_pages(full)
        full_confidence = parse_full_confidence(full)

        return PdfIngestResult(
            relevant=bool(full_relevant),
            confidence=full_confidence or preview_confidence or 0.6,
            document_scope=full_scope or preview_scope or "official_pdf",
            entity_match_summary=full_entity or preview_entity or title,
            key_findings=tuple(full_key_findings[:5]),
            evidence_pages=tuple(full_pages_found[:5] or selected_pages[:5] or candidate_pages[:5]),
        )

    return research_pdf_analyzer


__all__ = [
    "RuntimePdfCapability",
    "build_research_pdf_analyzer",
    "parse_preview_relevance",
    "parse_preview_scope",
    "parse_preview_entity_match",
    "parse_preview_confidence",
    "parse_preview_candidate_pages",
    "parse_full_relevant",
    "parse_full_scope",
    "parse_full_entity_match",
    "parse_full_key_findings",
    "parse_full_evidence_pages",
    "parse_full_confidence",
]
