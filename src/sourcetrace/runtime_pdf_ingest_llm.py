from __future__ import annotations

import json
from typing import Any, Callable

from dataclasses import dataclass
from sourcetrace.application import PdfIngestResult


QUALITY_THRESHOLD = 0.7


@dataclass(frozen=True)
class PdfLlmJudgeDebug:
    fallback_used: bool
    raw_text: str
    parsed_json: dict[str, Any] | None
    snippets: tuple[str, ...]
    candidate_pages: tuple[int, ...]
    result: PdfIngestResult


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    return max(0.0, min(1.0, parsed))


def _coerce_positive_ints(values: Any, limit: int) -> tuple[int, ...]:
    if not isinstance(values, list):
        return ()
    out: list[int] = []
    for item in values:
        try:
            page = int(item)
        except Exception:
            continue
        if page > 0:
            out.append(page)
    return tuple(out[:limit])


def _coerce_strings(values: Any, limit: int) -> tuple[str, ...]:
    if not isinstance(values, list):
        return ()
    out: list[str] = []
    for item in values:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return tuple(out[:limit])


def _extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except Exception:
        return None


def _build_pdf_llm_prompt(
    *,
    query: str,
    title: str,
    url: str,
    triage_verdict: str,
    snippets: tuple[str, ...],
    candidate_pages: tuple[int, ...],
) -> str:
    context_block = "\n\n".join(f"[chunk {idx+1}] {snippet}" for idx, snippet in enumerate(snippets)) or "[chunk 1] no_context"
    pages_block = ", ".join(str(page) for page in candidate_pages) or "n/a"
    return f"""
You are evaluating whether a PDF document is good enough to be used as verified research context for the user's question.

User query:
{query}

Document title:
{title}

Document URL:
{url}

Prior triage verdict:
{triage_verdict}

Candidate evidence pages:
{pages_block}

PDF content context:
{context_block}

Return JSON only with this exact schema:
{{
  "quality_score": 0.0,
  "relevant": true,
  "verified": true,
  "document_scope": "string",
  "entity_match_summary": "string",
  "key_findings": ["string"],
  "evidence_pages": [1],
  "reason": "string"
}}

Rules:
- Evaluate based on the PDF content context only.
- quality_score is from 0.0 to 1.0.
- verified=true only if the PDF is strong enough to use as trusted research context for the user query.
- If quality is below threshold or evidence is weak/off-topic, set verified=false.
- Produce 2-5 concise key_findings when the PDF supports the query.
- If evidence is too weak, return key_findings as [] and explain briefly in reason.
""".strip()


def build_pdf_llm_judge(
    generate_text: Callable[[str], Any],
) -> Callable[..., PdfLlmJudgeDebug]:
    def judge(
        *,
        query: str,
        title: str,
        url: str,
        triage_verdict: str,
        snippets: tuple[str, ...],
        candidate_pages: tuple[int, ...],
        fallback: PdfIngestResult,
    ) -> PdfLlmJudgeDebug:
        prompt = _build_pdf_llm_prompt(
            query=query,
            title=title,
            url=url,
            triage_verdict=triage_verdict,
            snippets=snippets,
            candidate_pages=candidate_pages,
        )
        try:
            response = generate_text(prompt)
            raw_text = getattr(response, 'text', None)
            if raw_text is None:
                raw_text = getattr(response, 'content', None)
            if raw_text is None:
                raw_text = str(response)
            payload = _extract_json(str(raw_text))
            if not isinstance(payload, dict):
                return PdfLlmJudgeDebug(True, str(raw_text), None, snippets, candidate_pages, fallback)
            quality_score = _coerce_float(payload.get('quality_score', 0.0), 0.0)
            relevant = bool(payload.get('relevant', False))
            verified = bool(payload.get('verified', False)) and quality_score >= QUALITY_THRESHOLD
            scope = str(payload.get('document_scope', fallback.document_scope) or fallback.document_scope).strip()
            entity = str(payload.get('entity_match_summary', fallback.entity_match_summary) or fallback.entity_match_summary).strip()
            findings = _coerce_strings(payload.get('key_findings'), 5)
            evidence_pages = _coerce_positive_ints(payload.get('evidence_pages'), 5)
            result = PdfIngestResult(
                relevant=relevant and verified,
                confidence=quality_score,
                document_scope=scope,
                entity_match_summary=entity,
                key_findings=findings if verified else (),
                evidence_pages=evidence_pages or fallback.evidence_pages,
            )
            return PdfLlmJudgeDebug(False, str(raw_text), payload, snippets, candidate_pages, result)
        except Exception as exc:
            return PdfLlmJudgeDebug(True, f"__exception__:{type(exc).__name__}:{exc}", None, snippets, candidate_pages, fallback)

    return judge
