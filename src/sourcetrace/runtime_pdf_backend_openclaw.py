from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse
import re
import tempfile
import urllib.request

import pdfplumber

from sourcetrace.application import PdfIngestResult

_WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9]{3,}")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_QUERY_RE = re.compile(r"Query:\s*(.+)", re.IGNORECASE)
_TITLE_HINT_RE = re.compile(r"Title hint:\s*(.+)", re.IGNORECASE)
_STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "have", "into", "about",
    "jest", "oraz", "które", "ktory", "ktora", "który", "której", "którego", "sprawie",
    "ustalila", "ustaliła", "query", "title", "hint", "document", "report", "only",
    "read", "page", "return", "json", "exact", "schema", "analyze", "pdf", "relevant",
    "uncertain", "irrelevant", "confidence", "candidate", "pages", "entity", "scope",
}
_FINDING_CUES = (
    "stwierdz", "ustal", "nieprawid", "wykaz", "ocen", "wniosk", "zalec", "brak", "niewystarczaj", "nie stworzono",
)
_SECTION_HEADING_CUES = (
    "ocena ogolna",
    "ocena ogólna",
    "wnioski",
    "ustalenia kontroli",
    "ustalenia pokontrolne",
    "najwazniejsze ustalenia",
    "najważniejsze ustalenia",
    "wyniki kontroli",
)


@dataclass(frozen=True)
class _PageText:
    page_number: int
    text: str


def _normalize_token(token: str) -> str:
    token = token.lower().replace("ł", "l").replace("ó", "o").replace("ą", "a").replace("ę", "e").replace("ś", "s").replace("ć", "c").replace("ń", "n").replace("ż", "z").replace("ź", "z")
    for suffix in ("owego", "owym", "owej", "owie", "ami", "ach", "ego", "emu", "owa", "owy", "owe", "ska", "ski", "szym", "nych", "nego", "nia", "niu", "ciu", "cie", "ach", "ami", "owie", "awa", "awie"):
        if token.endswith(suffix) and len(token) > len(suffix) + 2:
            token = token[: -len(suffix)]
            break
    return token


def _tokenize(text: str) -> list[str]:
    lowered = text.lower()
    tokens = []
    for raw in _WORD_RE.findall(lowered):
        if raw in _STOPWORDS:
            continue
        normalized = _normalize_token(raw)
        if normalized and normalized not in _STOPWORDS:
            tokens.append(normalized)
    return tokens


def _extract_query_context(prompt: str) -> tuple[str, str]:
    query_match = _QUERY_RE.search(prompt)
    title_match = _TITLE_HINT_RE.search(prompt)
    query = query_match.group(1).strip() if query_match else prompt.strip()
    title_hint = title_match.group(1).strip() if title_match else ""
    return query, title_hint


_TOC_ENTRY_RE = re.compile(r"^(?P<title>.+?)\.{3,}(?P<page>\d{1,3})$")


def _parse_page_spec(pages: str) -> list[int]:
    page_numbers: list[int] = []
    if pages.strip():
        for raw in pages.split(','):
            raw = raw.strip()
            if not raw:
                continue
            if '-' in raw:
                start, end = raw.split('-', 1)
                page_numbers.extend(range(int(start), int(end) + 1))
            else:
                page_numbers.append(int(raw))
    return page_numbers


def _extract_toc_candidate_pages(pages: list[_PageText]) -> list[int]:
    candidates: list[int] = []
    for page in pages:
        for line in page.text.splitlines():
            clean = " ".join(line.split()).strip()
            if not clean:
                continue
            match = _TOC_ENTRY_RE.match(clean)
            if not match:
                continue
            title = _normalize_text(match.group('title'))
            try:
                target_page = int(match.group('page'))
            except Exception:
                continue
            if any(cue in title for cue in _SECTION_HEADING_CUES):
                if target_page not in candidates:
                    candidates.append(target_page)
                    if target_page + 1 not in candidates:
                        candidates.append(target_page + 1)
    return [page for page in candidates if page > 0][:8]


def _score_text(query_tokens: set[str], text: str) -> float:
    text_tokens = set(_tokenize(text))
    if not query_tokens or not text_tokens:
        return 0.0
    overlap = query_tokens & text_tokens
    if not overlap:
        return 0.0
    return len(overlap) / max(1, min(len(query_tokens), 8))


def _split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_SPLIT_RE.split(text) if p.strip()]
    return [p for p in parts if len(p) >= 40]


def _normalize_text(text: str) -> str:
    return (
        text.lower()
        .replace("ł", "l")
        .replace("ó", "o")
        .replace("ą", "a")
        .replace("ę", "e")
        .replace("ś", "s")
        .replace("ć", "c")
        .replace("ń", "n")
        .replace("ż", "z")
        .replace("ź", "z")
    )


def _read_pdf_pages(path: Path, page_numbers: Iterable[int] | None = None) -> list[_PageText]:
    requested = set(page_numbers or [])
    out: list[_PageText] = []
    with pdfplumber.open(str(path)) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            if requested and idx not in requested:
                continue
            text = (page.extract_text() or "").strip()
            if text:
                out.append(_PageText(page_number=idx, text=text))
    return out


def _resolve_local_pdf(pdf: str) -> tuple[Path, bool]:
    if pdf.startswith(("http://", "https://")):
        suffix = Path(urlparse(pdf).path).suffix or ".pdf"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.close()
        urllib.request.urlretrieve(pdf, tmp.name)
        return Path(tmp.name), True
    if pdf.startswith("file://"):
        return Path(urlparse(pdf).path), False
    return Path(pdf).expanduser(), False


def _best_title(pages: list[_PageText], title_hint: str, path: Path) -> str:
    for page in pages[:2]:
        for line in page.text.splitlines()[:10]:
            clean = " ".join(line.split()).strip()
            if len(clean) < 12:
                continue
            if clean.lower().startswith(("page ", "strona ")):
                continue
            if sum(ch.isdigit() for ch in clean) > max(6, len(clean) // 3):
                continue
            return clean[:180]
    return title_hint or path.stem


def _page_score(page: _PageText, query_tokens: set[str]) -> float:
    score = _score_text(query_tokens, page.text)
    text = _normalize_text(page.text)
    if any(token in text for token in ("szpital", "hospital", "klinika", "ratownictw", "medyczn")):
        score += 0.2
    if any(token in text for token in ("poludniow", "warszaw", "nik", "system")):
        score += 0.2
    return score


def _top_pages(pages: list[_PageText], query_tokens: set[str], limit: int = 5) -> list[_PageText]:
    ranked = sorted(pages, key=lambda page: (_page_score(page, query_tokens), -page.page_number), reverse=True)
    return [page for page in ranked if _page_score(page, query_tokens) > 0][:limit]


def _looks_like_heading(line: str) -> bool:
    clean = " ".join(line.split()).strip()
    if len(clean) < 5 or len(clean) > 120:
        return False
    if clean.endswith(('.', ';', ':')):
        return False
    letters = sum(ch.isalpha() for ch in clean)
    if letters < max(4, len(clean) // 3):
        return False
    normalized = _normalize_text(clean)
    if any(cue in normalized for cue in _SECTION_HEADING_CUES):
        return True
    upper_ratio = sum(ch.isupper() for ch in clean if ch.isalpha()) / max(1, letters)
    return upper_ratio > 0.7


def _extract_section_blocks(pages: list[_PageText]) -> list[tuple[int, str, str]]:
    blocks: list[tuple[int, str, str]] = []
    for page in pages:
        lines = [" ".join(line.split()).strip() for line in page.text.splitlines()]
        current_heading: str | None = None
        current_lines: list[str] = []
        for line in lines:
            if not line:
                continue
            if _looks_like_heading(line):
                if current_heading and current_lines:
                    blocks.append((page.page_number, current_heading, " ".join(current_lines).strip()))
                current_heading = line
                current_lines = []
                continue
            if current_heading:
                current_lines.append(line)
        if current_heading and current_lines:
            blocks.append((page.page_number, current_heading, " ".join(current_lines).strip()))
    return blocks


def _section_block_score(page_number: int, heading: str, body: str, query_tokens: set[str]) -> float:
    normalized_heading = _normalize_text(heading)
    normalized_body = _normalize_text(body)
    score = _score_text(query_tokens, f"{heading} {body}")
    if any(cue in normalized_heading for cue in _SECTION_HEADING_CUES):
        score += 0.45
    if any(cue in normalized_body for cue in _FINDING_CUES):
        score += 0.25
    if len(body) >= 240:
        score += 0.1
    if page_number <= 5:
        score += 0.05
    return score


def _section_snippet_candidates(pages: list[_PageText], query_tokens: set[str], limit: int = 8) -> list[str]:
    ranked: list[tuple[float, str]] = []
    for page_number, heading, body in _extract_section_blocks(pages):
        if len(body) < 80:
            continue
        snippet = f"{heading}: {body[:900]}".strip()
        score = _section_block_score(page_number, heading, body, query_tokens)
        if score > 0.2:
            ranked.append((score, snippet[:500]))
    ranked.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
    unique: list[str] = []
    for _, snippet in ranked:
        if snippet not in unique:
            unique.append(snippet)
        if len(unique) >= limit:
            break
    return unique


def _subject_lines(pages: list[_PageText], query_tokens: set[str]) -> list[tuple[int, str, float]]:
    hits: list[tuple[int, str, float]] = []
    for page in pages:
        page_bonus = _page_score(page, query_tokens)
        for line in page.text.splitlines():
            clean = " ".join(line.split()).strip()
            if len(clean) < 20:
                continue
            score = _score_text(query_tokens, clean) + page_bonus
            if score > 0:
                hits.append((page.page_number, clean, score))
    hits.sort(key=lambda item: (item[2], len(item[1])), reverse=True)
    return hits


def _best_scope(pages: list[_PageText], query_tokens: set[str], title_hint: str, path: Path) -> str:
    ranked_pages = _top_pages(pages, query_tokens, limit=3)
    for page in ranked_pages:
        for sentence in _split_sentences(page.text):
            clean = sentence.replace('\n', ' ').strip()
            if _score_text(query_tokens, clean) > 0 and len(clean) >= 60:
                return clean[:220]
    return title_hint or path.stem


def _preview_prompt(*, query: str, title: str) -> str:
    return f"""
Read the opening pages of this PDF and identify whether the document looks relevant enough for deeper analysis.

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


def _snippet_candidates(pages: list[_PageText], query_tokens: set[str], limit: int = 8) -> list[str]:
    section_snippets = _section_snippet_candidates(pages, query_tokens, limit=limit)
    if section_snippets:
        return section_snippets
    ranked: list[tuple[float, str]] = []
    for page in pages:
        page_bonus = _page_score(page, query_tokens)
        for sentence in _split_sentences(page.text):
            clean = sentence.replace('\n', ' ').strip()
            score = _score_text(query_tokens, clean) + page_bonus
            if any(cue in _normalize_text(clean) for cue in _FINDING_CUES):
                score += 0.25
            if score > 0:
                ranked.append((score, clean[:320]))
    ranked.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
    unique: list[str] = []
    for _, sentence in ranked:
        if sentence not in unique:
            unique.append(sentence)
        if len(unique) >= limit:
            break
    return unique


def _context_chunks(pages: list[_PageText], query_tokens: set[str], limit: int = 6) -> list[str]:
    ranked: list[tuple[float, str]] = []
    section_snippets = _section_snippet_candidates(pages, query_tokens, limit=limit)
    for snippet in section_snippets:
        ranked.append((1.0 + _score_text(query_tokens, snippet), snippet[:1400]))
    if len(ranked) < limit:
        for page in pages:
            page_bonus = _page_score(page, query_tokens)
            text = ' '.join(page.text.split())
            if len(text) < 120:
                continue
            excerpt = text[:1600]
            score = _score_text(query_tokens, excerpt) + page_bonus
            if any(cue in _normalize_text(excerpt) for cue in _FINDING_CUES):
                score += 0.2
            if score > 0:
                ranked.append((score, f"[page {page.page_number}] {excerpt}"[:1700]))
    ranked.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
    unique: list[str] = []
    for _, chunk in ranked:
        if chunk not in unique:
            unique.append(chunk)
        if len(unique) >= limit:
            break
    return unique


def openclaw_pdf_capability(*, pdf: str, prompt: str, pages: str = "") -> dict[str, object]:
    path, cleanup = _resolve_local_pdf(pdf)
    try:
        page_numbers = _parse_page_spec(pages)

        selected_pages = _read_pdf_pages(path, page_numbers or None)
        query, title_hint = _extract_query_context(prompt)
        query_tokens = set(_tokenize(query + " " + title_hint))
        ranked_pages = _top_pages(selected_pages, query_tokens, limit=5)
        working_pages = ranked_pages or selected_pages[:5]
        full_text = "\n\n".join(p.text for p in working_pages)
        score = _score_text(query_tokens, full_text)
        subject_hits = _subject_lines(working_pages, query_tokens)
        evidence_pages = []
        for page in working_pages:
            if _page_score(page, query_tokens) > 0 and page.page_number not in evidence_pages:
                evidence_pages.append(page.page_number)
        evidence_pages = evidence_pages[:5]

        findings = _snippet_candidates(working_pages, query_tokens, limit=8)
        context_chunks = _context_chunks(working_pages, query_tokens, limit=6)

        title = _best_title(selected_pages, title_hint, path)
        scope = _best_scope(working_pages, query_tokens, title_hint, path)
        entity = subject_hits[0][1][:160] if subject_hits else title

        is_preview_mode = 'relevance_verdict' in prompt and 'candidate_pages' in prompt
        if is_preview_mode:
            toc_candidate_pages = _extract_toc_candidate_pages(selected_pages)
            candidate_pages = toc_candidate_pages or evidence_pages or ([working_pages[0].page_number] if working_pages and score > 0 else [])
            return {
                "document_title": title,
                "main_entity": entity,
                "document_scope": scope,
                "relevance_verdict": "relevant" if score >= 0.2 else "uncertain" if score > 0 else "irrelevant",
                "reason": f"token_overlap_score={score:.2f}",
                "candidate_pages": candidate_pages,
                "confidence": min(1.0, max(0.0, score)),
            }

        return {
            "relevant": score > 0,
            "document_scope": scope,
            "entity_match_summary": entity,
            "key_findings": findings[:8],
            "context_chunks": context_chunks[:6],
            "evidence_pages": evidence_pages,
            "confidence": min(1.0, max(0.0, score)),
        }
    finally:
        if cleanup:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass


def build_native_pdf_ingestor_with_llm(
    *,
    llm_judge,
):
    def ingest(*, query: str, url: str, title: str, triage_verdict: str) -> PdfIngestResult:
        preview = openclaw_pdf_capability(
            pdf=url,
            pages="1-3",
            prompt=_preview_prompt(query=query, title=title),
        )
        candidate_pages = tuple(preview.get("candidate_pages") or ()) if isinstance(preview, dict) else ()
        if not candidate_pages or candidate_pages == (1,):
            page_spec = "1-5"
        else:
            page_spec = ",".join(str(page) for page in candidate_pages)
        full = openclaw_pdf_capability(
            pdf=url,
            pages=page_spec,
            prompt=_full_prompt(query=query, title=title),
        )
        snippets = tuple(full.get("context_chunks") or full.get("key_findings") or ()) if isinstance(full, dict) else ()
        fallback = PdfIngestResult(
            relevant=bool(full.get("relevant", False)) if isinstance(full, dict) else False,
            confidence=float(full.get("confidence", 0.0)) if isinstance(full, dict) else 0.0,
            document_scope=str(full.get("document_scope", title)) if isinstance(full, dict) else title,
            entity_match_summary=str(full.get("entity_match_summary", title)) if isinstance(full, dict) else title,
            key_findings=tuple(str(item) for item in (full.get("key_findings") or [])[:5]) if isinstance(full, dict) else (),
            evidence_pages=tuple(int(item) for item in (full.get("evidence_pages") or [])[:5]) if isinstance(full, dict) else (),
        )
        debug = llm_judge(
            query=query,
            title=title,
            url=url,
            triage_verdict=triage_verdict,
            snippets=snippets,
            candidate_pages=tuple(int(p) for p in candidate_pages[:5]),
            fallback=fallback,
        )
        ingest.last_debug = debug
        return debug.result

    ingest.last_debug = None
    return ingest
