from __future__ import annotations

import re
from dataclasses import dataclass, replace
from urllib.parse import urlparse

from sourcetrace_v2.adapters.pdf.interfaces import PdfReadGateway
from sourcetrace_v2.adapters.search.interfaces import SearchGateway
from sourcetrace_v2.core.domain.identifiers import StageStatus
from sourcetrace_v2.core.domain.models import PdfEvidenceContext, RetrievedEvidenceCandidate, StageExecutionReceipt
from sourcetrace_v2.execution.context.models import ExecutionContext
from sourcetrace_v2.execution.receipts.collector import ReceiptCollector

_COMMUNITY_GROUP_MARKERS = frozenset(
    {
        "community",
        "communities",
        "diaspora",
        "expatriate",
        "expatriates",
        "immigrant",
        "immigrants",
        "migrant",
        "migrants",
        "migration",
        "refugee",
        "refugees",
    }
)
_QUALITY_OF_LIFE_MARKERS = frozenset(
    {
        "conditions",
        "life",
        "living",
        "qol",
        "wellbeing",
    }
)
_QUALITY_OF_LIFE_PHRASES = (
    "life satisfaction",
    "living conditions",
    "quality of life",
    "well being",
    "well-being",
)
_COMMUNITY_OUTCOME_TOKENS = (
    "discrimination",
    "education",
    "employment",
    "health",
    "housing",
    "income",
    "integration",
    "satisfaction",
)
_COMMUNITY_OUTCOME_PHRASES = (
    "life satisfaction",
    "living conditions",
)
_COMMUNITY_OUTCOME_SNIPPET_CUES = (
    ("employment", "employment"),
    ("health care", "healthcare"),
    ("healthcare", "healthcare"),
    ("education", "education"),
    ("housing", "housing"),
    ("income", "income"),
    ("discrimination", "discrimination"),
    ("integration", "integration"),
    ("health", "health"),
    ("life satisfaction", "life satisfaction"),
    ("living conditions", "living conditions"),
    ("quality of life", "quality of life"),
)
_SNIPPET_ONLY_PDF_SCOPE = "Snippet-only PDF signal; full-document relevance not verified."
_SNIPPET_ONLY_QUERY_FOCUS_STOPWORDS = frozenset(
    {
        "about",
        "article",
        "articles",
        "conditions",
        "document",
        "documents",
        "finding",
        "findings",
        "life",
        "living",
        "main",
        "paper",
        "papers",
        "pdf",
        "quality",
        "report",
        "reports",
        "result",
        "results",
        "study",
        "studies",
    }
)
_PDF_SNIPPET_FAILURE_MARKERS = (
    "download pdf",
    "full read failed",
    "no clear subject match",
    "pdf result",
    "preview failed",
    "preview only",
    "read failed",
    "triage blocked",
    "valid json",
)


@dataclass(frozen=True)
class RetrievalStageResult:
    retrieval_query: str
    candidates: tuple[RetrievedEvidenceCandidate, ...]


class RetrievalStage:
    def __init__(self, *, search: SearchGateway, pdf: PdfReadGateway | None = None, limit: int = 3) -> None:
        self.search = search
        self.pdf = pdf
        self.limit = limit

    def run(self, *, context: ExecutionContext, collector: ReceiptCollector, input_text: str) -> RetrievalStageResult:
        collector.append_stage(
            StageExecutionReceipt(
                receipt_id=f"stage:{context.stage_id}:start",
                job_id=context.job_id,
                run_id=context.run_id,
                stage_id=context.stage_id,
                call_site=context.call_site,
                status=StageStatus.STARTED,
                attempt=context.attempt,
                round_number=context.round_number,
            )
        )
        try:
            retrieval_limit = self._retrieval_window_limit(query=input_text)
            candidates = self.search.search(
                job_id=context.job_id,
                run_id=context.run_id,
                query=input_text,
                limit=retrieval_limit,
            )
            candidates = self._annotate_source_types(candidates=candidates)
            candidates = self._shape_source_mix(
                candidates=candidates,
                query=input_text,
            )
            candidates = self._trim_candidate_window(candidates=candidates)
            candidates = self._enrich_pdf_candidates(
                candidates=candidates,
                query=input_text,
            )
        except Exception as exc:
            collector.append_stage(
                StageExecutionReceipt(
                    receipt_id=f"stage:{context.stage_id}:failed",
                    job_id=context.job_id,
                    run_id=context.run_id,
                    stage_id=context.stage_id,
                    call_site=context.call_site,
                    status=StageStatus.FAILED,
                    attempt=context.attempt,
                    round_number=context.round_number,
                    detail=str(exc),
                )
            )
            raise
        collector.append_stage(
            StageExecutionReceipt(
                receipt_id=f"stage:{context.stage_id}:complete",
                job_id=context.job_id,
                run_id=context.run_id,
                stage_id=context.stage_id,
                call_site=context.call_site,
                status=StageStatus.COMPLETED,
                attempt=context.attempt,
                round_number=context.round_number,
                detail=f"candidate_count={len(candidates)}",
            )
        )
        return RetrievalStageResult(retrieval_query=input_text, candidates=candidates)

    def _retrieval_window_limit(self, *, query: str) -> int:
        if _query_implies_institutional_preference(query) or _query_implies_community_outcome_focus(query):
            return max(self.limit, self.limit + 3)
        return self.limit

    def _trim_candidate_window(
        self,
        *,
        candidates: tuple[RetrievedEvidenceCandidate, ...],
    ) -> tuple[RetrievedEvidenceCandidate, ...]:
        trimmed = candidates[: self.limit]
        return tuple(replace(candidate, rank=index + 1) for index, candidate in enumerate(trimmed))

    def _shape_source_mix(
        self,
        *,
        candidates: tuple[RetrievedEvidenceCandidate, ...],
        query: str,
    ) -> tuple[RetrievedEvidenceCandidate, ...]:
        institutional_preference = _query_implies_institutional_preference(query)
        community_outcome_focus = _query_implies_community_outcome_focus(query)
        if len(candidates) < 2 or not (institutional_preference or community_outcome_focus):
            return candidates
        typed = candidates if any(candidate.source_type != "unknown" for candidate in candidates) else self._annotate_source_types(candidates=candidates)
        scored: list[tuple[int, int, int, RetrievedEvidenceCandidate]] = []
        for index, candidate in enumerate(typed):
            scored.append((
                _source_mix_priority(candidate) if institutional_preference else 0,
                _candidate_target_quality_priority(candidate=candidate, query=query),
                index,
                candidate,
            ))
        scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
        reordered = tuple(item[3] for item in scored)
        return tuple(replace(candidate, rank=index + 1) for index, candidate in enumerate(reordered))

    def _annotate_source_types(
        self,
        *,
        candidates: tuple[RetrievedEvidenceCandidate, ...],
    ) -> tuple[RetrievedEvidenceCandidate, ...]:
        return tuple(
            replace(candidate, source_type=_classify_source_type(candidate))
            for candidate in candidates
        )

    def _enrich_pdf_candidates(
        self,
        *,
        candidates: tuple[RetrievedEvidenceCandidate, ...],
        query: str,
    ) -> tuple[RetrievedEvidenceCandidate, ...]:
        if self.pdf is None:
            return candidates
        enriched: list[RetrievedEvidenceCandidate] = []
        for candidate in candidates:
            if not _looks_like_pdf_candidate(candidate):
                enriched.append(candidate)
                continue
            try:
                pdf_result = self.pdf.read(
                    query=query,
                    url=candidate.url,
                    title=candidate.title,
                    triage_verdict="relevant",
                )
            except Exception:
                enriched.append(candidate)
                continue
            if not pdf_result.relevant:
                raw_pdf_context = _build_raw_pdf_context(pdf_result)
                partial_pdf_context = _build_partial_pdf_context(pdf_result)
                if raw_pdf_context is not None and candidate.snippet.strip() and _looks_like_meaningful_pdf_snippet(candidate.snippet):
                    enriched.append(
                        replace(
                            candidate,
                            pdf_context=raw_pdf_context,
                        )
                    )
                elif partial_pdf_context is not None:
                    enriched.append(
                        replace(
                            candidate,
                            pdf_context=partial_pdf_context,
                        )
                    )
                elif (snippet_only_pdf_context := _build_snippet_only_pdf_context(candidate=candidate, query=query)) is not None:
                    enriched.append(
                        replace(
                            candidate,
                            pdf_context=snippet_only_pdf_context,
                        )
                    )
                else:
                    enriched.append(candidate)
                continue
            snippet_parts = []
            if pdf_result.document_scope:
                snippet_parts.append(f"pdf_scope={pdf_result.document_scope}")
            if pdf_result.entity_match_summary:
                snippet_parts.append(pdf_result.entity_match_summary)
            if pdf_result.key_findings:
                snippet_parts.extend(pdf_result.key_findings[:2])
            snippet = " | ".join(part.strip() for part in snippet_parts if part and part.strip()) or candidate.snippet
            enriched.append(
                replace(
                    candidate,
                    snippet=snippet,
                    pdf_context=PdfEvidenceContext(
                        document_scope=pdf_result.document_scope,
                        entity_match_summary=pdf_result.entity_match_summary,
                        key_findings=tuple(pdf_result.key_findings[:2]),
                    ),
                )
            )
        return tuple(enriched)


def _query_implies_institutional_preference(query: str) -> bool:
    lowered = query.lower()
    markers = (
        "official",
        "authority",
        "guidance",
        "regulation",
        "compliance",
        "policy",
        "government",
        "ministry",
        "commission",
        "oficjal",
        "urzęd",
        "minister",
        "inspekcj",
        "gov.pl",
        "pip",
        "zus",
    )
    return any(marker in lowered for marker in markers)


def _query_implies_community_outcome_focus(query: str) -> bool:
    lowered = query.lower()
    tokens = set(_tokenize_scoring_text(query))
    community_like = bool(tokens & _COMMUNITY_GROUP_MARKERS)
    quality_of_life_like = bool(tokens & _QUALITY_OF_LIFE_MARKERS) or any(
        phrase in lowered for phrase in _QUALITY_OF_LIFE_PHRASES
    )
    return community_like and quality_of_life_like


_INSTITUTIONAL_HOST_MARKERS = (
    ".gov",
    ".gov.uk",
    "europa.eu",
    "archives.gov",
    "ftc.gov",
    "ico.org.uk",
    "edpb.europa.eu",
    "ec.europa.eu",
    "learn.microsoft.com",
    "microsoft.com",
)

_VENDOR_HOST_MARKERS = (
    "vendor",
    "opentext",
    "everlaw",
    "venio",
    "disco",
    "admindroid",
    "dilitrust",
    "mitratech",
)

_COMMENTARY_HOST_MARKERS = (
    "blog.",
    "blogs.",
    "medium.com",
    "substack.com",
    "linkedin.com",
    "bpcc.org.pl",
    "dudkowiak.com",
    "lawfirm.",
    "law.",
    "vansurksum.com",
    "getsix.eu",
    "getsix.com",
)

_INSTITUTIONAL_TITLE_MARKERS = (
    "official",
    "authority",
    "commission",
    "ministry",
    "government",
    "national archives",
    "federal trade commission",
    "information commissioner's office",
    "microsoft learn",
)

_COMMENTARY_TITLE_MARKERS = (
    "blog",
    "best practices",
    "explainer",
    "law firm",
)

_PUBLICATION_SURFACE_HOST_MARKERS = (
    "pmc.ncbi.nlm.nih.gov",
    "pubmed.ncbi.nlm.nih.gov",
)

_PUBLICATION_SURFACE_STRONG_MARKERS = (
    "abstract",
    "cejsh",
    "doi",
    "issn",
    "journal",
    "pmc",
    "pubmed",
)

_PUBLICATION_SURFACE_SOFT_MARKERS = (
    "article",
    "paper",
    "review",
    "study",
)


def _classify_source_type(candidate: RetrievedEvidenceCandidate) -> str:
    parsed = urlparse(candidate.url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    title = candidate.title.lower()
    if any(host.endswith(marker) or marker in host for marker in _INSTITUTIONAL_HOST_MARKERS):
        return "institutional"
    if any(token in title for token in _INSTITUTIONAL_TITLE_MARKERS):
        return "institutional"
    if any(token in host for token in _VENDOR_HOST_MARKERS):
        return "vendor"
    if _looks_like_hosted_vendor_practical_pdf(host=host, path=path, title=title):
        return "vendor"
    if any(token in host for token in _COMMENTARY_HOST_MARKERS):
        return "commentary"
    if any(token in title for token in _COMMENTARY_TITLE_MARKERS):
        return "commentary"
    return "unknown"


def _looks_like_hosted_vendor_practical_pdf(*, host: str, path: str, title: str) -> bool:
    if not path.endswith('.pdf'):
        return False
    vendorish = ('opentext', 'everlaw', 'venio', 'disco', 'legal hold', 'practical guidance')
    communityish = ('cloc.org', 'wp-content')
    return any(token in title for token in vendorish) and any(token in host or token in path for token in communityish)


def _source_mix_priority(candidate: RetrievedEvidenceCandidate) -> int:
    priority_by_source_type = {
        "institutional": 4,
        "vendor": 1,
        "unknown": 0,
        "commentary": -1,
    }
    score = priority_by_source_type.get(candidate.source_type, 0)
    if candidate.source_type == "institutional":
        score += _institutional_surface_priority(candidate)
    if candidate.snippet.strip():
        score += 1
    return score


def _institutional_surface_priority(candidate: RetrievedEvidenceCandidate) -> int:
    if _looks_like_publication_surface(candidate):
        return -2
    return 0


def _looks_like_publication_surface(candidate: RetrievedEvidenceCandidate) -> bool:
    parsed = urlparse(candidate.url)
    host = parsed.netloc.lower()
    text = _candidate_surface_text(candidate)
    if any(marker == host or marker in host for marker in _PUBLICATION_SURFACE_HOST_MARKERS):
        return True
    if any(marker in text for marker in _PUBLICATION_SURFACE_STRONG_MARKERS):
        return True
    return sum(1 for marker in _PUBLICATION_SURFACE_SOFT_MARKERS if marker in text) >= 2


def _candidate_surface_text(candidate: RetrievedEvidenceCandidate) -> str:
    parsed = urlparse(candidate.url)
    return " ".join(
        (
            parsed.netloc.lower(),
            parsed.path.lower(),
            candidate.title.lower(),
            candidate.snippet.lower(),
        )
    )


_SCORING_TOKEN_RE = re.compile(r"[a-z0-9]+")
_QUERY_FOCUS_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "best",
        "by",
        "for",
        "from",
        "how",
        "in",
        "of",
        "on",
        "or",
        "the",
        "to",
        "what",
        "when",
        "with",
    }
)
_QUERY_INTENT_MARKERS = frozenset(
    {
        "authority",
        "best",
        "compliance",
        "government",
        "guide",
        "guidance",
        "ministry",
        "official",
        "policy",
        "practice",
        "practices",
        "regulation",
    }
)

_ADJACENT_BROAD_INSTITUTIONAL_MARKERS = frozenset(
    {
        "article",
        "articles",
        "basic",
        "centre",
        "center",
        "general",
        "information",
        "overview",
        "portal",
        "rights",
    }
)



def _candidate_target_quality_priority(*, candidate: RetrievedEvidenceCandidate, query: str) -> int:
    focus_tokens = _query_focus_tokens(query)
    title_tokens = set(_tokenize_scoring_text(candidate.title))
    supporting_tokens = set(
        _tokenize_scoring_text(" ".join(part for part in (candidate.snippet, candidate.url) if part))
    )
    normalized_candidate_text = _normalize_scoring_text(" ".join((candidate.title, candidate.snippet, candidate.url)))
    score = 0
    if focus_tokens:
        focus_token_set = set(focus_tokens)
        title_overlap = focus_token_set & title_tokens
        supporting_overlap = focus_token_set & supporting_tokens
        phrase_matches = sum(
            1
            for phrase in _query_focus_phrases(query)
            if phrase in normalized_candidate_text
        )
        score += (len(title_overlap) * 3) + len(supporting_overlap - title_overlap) + (phrase_matches * 3)
        score += _institutional_exact_subject_bonus(
            candidate=candidate,
            focus_tokens=focus_token_set,
            title_tokens=title_tokens,
            normalized_candidate_text=normalized_candidate_text,
        )
    if _query_implies_community_outcome_focus(query):
        outcome_tokens = set(_COMMUNITY_OUTCOME_TOKENS)
        title_outcome_overlap = outcome_tokens & title_tokens
        supporting_outcome_overlap = outcome_tokens & supporting_tokens
        outcome_phrase_matches = sum(
            1
            for phrase in _COMMUNITY_OUTCOME_PHRASES
            if phrase in normalized_candidate_text
        )
        score += (len(title_outcome_overlap) * 4) + (len(supporting_outcome_overlap - title_outcome_overlap) * 2)
        score += outcome_phrase_matches * 4
    return score


def _institutional_exact_subject_bonus(
    *,
    candidate: RetrievedEvidenceCandidate,
    focus_tokens: set[str],
    title_tokens: set[str],
    normalized_candidate_text: str,
) -> int:
    if candidate.source_type != "institutional":
        return 0
    score = 0
    title_overlap = focus_tokens & title_tokens
    parsed = urlparse(candidate.url)
    path_text = _normalize_scoring_text(parsed.path.replace("-", " ").replace("_", " "))
    path_tokens = set(path_text.split()) if path_text else set()
    path_overlap = focus_tokens & path_tokens
    if len(title_overlap) >= 2:
        score += 6
    elif len(title_overlap) == 1:
        score += 2
    if len(path_overlap) >= 2:
        score += 5
    elif len(path_overlap) == 1:
        score += 2
    if any(phrase in normalized_candidate_text for phrase in ("remote work", "praca zdalna", "labour code", "kodeks pracy")):
        score += 3
    if _looks_adjacent_broad_institutional(candidate=candidate, title_tokens=title_tokens):
        score -= 4
    return score



def _looks_adjacent_broad_institutional(*, candidate: RetrievedEvidenceCandidate, title_tokens: set[str]) -> bool:
    if candidate.source_type != "institutional":
        return False
    parsed = urlparse(candidate.url)
    host = parsed.netloc.lower()
    broad_marker_hits = len(title_tokens & _ADJACENT_BROAD_INSTITUTIONAL_MARKERS)
    if broad_marker_hits == 0 and not any(marker in host for marker in ("parp.",)):
        return False
    if any(token in title_tokens for token in ("faq", "remote", "work", "praca", "zdalna", "labour", "employer", "obligations")):
        return broad_marker_hits >= 2 and not any(token in title_tokens for token in ("faq", "obligations"))
    return True



def _query_focus_tokens(query: str) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for token in _tokenize_scoring_text(query):
        if token in _QUERY_FOCUS_STOPWORDS or token in _QUERY_INTENT_MARKERS:
            continue
        if len(token) < 2:
            continue
        if token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return tuple(ordered)


def _query_focus_phrases(query: str) -> tuple[str, ...]:
    focus_tokens = _query_focus_tokens(query)
    if len(focus_tokens) < 2:
        return ()
    return tuple(
        f"{focus_tokens[index]} {focus_tokens[index + 1]}"
        for index in range(len(focus_tokens) - 1)
    )


def _tokenize_scoring_text(value: str) -> tuple[str, ...]:
    return tuple(_SCORING_TOKEN_RE.findall(value.lower()))


def _normalize_scoring_text(value: str) -> str:
    return " ".join(_tokenize_scoring_text(value))


def _looks_like_pdf_candidate(candidate: RetrievedEvidenceCandidate) -> bool:
    lowered_url = candidate.url.lower()
    lowered_title = candidate.title.lower()
    return (
        lowered_url.endswith('.pdf')
        or '.pdf?' in lowered_url
        or '.pdf/' in lowered_url
        or '/pobierz,' in lowered_url
        or lowered_title.endswith('.pdf')
        or lowered_title.startswith('[pdf]')
    )


def _looks_like_meaningful_pdf_snippet(snippet: str) -> bool:
    lowered = snippet.lower()
    markers = (
        'main findings',
        'abstract',
        'conclusion',
        'results',
        'study',
        'respondents',
    )
    return len(snippet.strip()) >= 80 and any(marker in lowered for marker in markers)


_GENERIC_PDF_SCOPE_MARKERS = frozenset(
    {
        "full invalid",
        "full read failed",
        "official pdf",
        "preview failed",
        "preview invalid",
        "preview only",
        "triage blocked",
    }
)
_GENERIC_PDF_ENTITY_PREFIXES = (
    "full read failed",
    "no clear subject match on preview",
    "preview did not return valid json",
    "preview read failed",
    "skipped because triage verdict was not positive",
)


def _build_raw_pdf_context(pdf_result: object) -> PdfEvidenceContext | None:
    document_scope = str(getattr(pdf_result, "document_scope", "") or "").strip()
    entity_match_summary = str(getattr(pdf_result, "entity_match_summary", "") or "").strip()
    key_findings = tuple(
        item.strip()
        for item in tuple(str(item) for item in (getattr(pdf_result, "key_findings", ()) or ()))[:2]
        if item.strip()
    )
    if not (document_scope or entity_match_summary or key_findings):
        return None
    return PdfEvidenceContext(
        document_scope=document_scope,
        entity_match_summary=entity_match_summary,
        key_findings=key_findings,
    )


def _build_partial_pdf_context(pdf_result: object) -> PdfEvidenceContext | None:
    raw_pdf_context = _build_raw_pdf_context(pdf_result)
    if raw_pdf_context is None:
        return None
    document_scope = raw_pdf_context.document_scope
    entity_match_summary = raw_pdf_context.entity_match_summary
    key_findings = raw_pdf_context.key_findings
    if not key_findings:
        document_scope = _meaningful_partial_pdf_scope(document_scope)
        entity_match_summary = _meaningful_partial_pdf_entity_match(entity_match_summary)
    if not (document_scope or entity_match_summary or key_findings):
        return None
    return PdfEvidenceContext(
        document_scope=document_scope,
        entity_match_summary=entity_match_summary,
        key_findings=key_findings,
    )


def _build_snippet_only_pdf_context(
    *,
    candidate: RetrievedEvidenceCandidate,
    query: str,
) -> PdfEvidenceContext | None:
    snippet = " ".join(candidate.snippet.split()).strip()
    if not _supports_snippet_only_pdf_context(candidate=candidate, query=query, snippet=snippet):
        return None
    outcome_cues = _extract_community_outcome_snippet_cues(snippet)
    if len(outcome_cues) < 3:
        return None
    summarized_cues = ", ".join(outcome_cues[:4])
    return PdfEvidenceContext(
        document_scope=_SNIPPET_ONLY_PDF_SCOPE,
        entity_match_summary=f"Snippet-only partial match for queried community outcomes: {summarized_cues}.",
        key_findings=(
            (
                f"Search snippet mentions {summarized_cues} for the queried community/topic; "
                "full-PDF findings were not verified."
            ),
        ),
    )


def _supports_snippet_only_pdf_context(
    *,
    candidate: RetrievedEvidenceCandidate,
    query: str,
    snippet: str,
) -> bool:
    if not _query_implies_community_outcome_focus(query):
        return False
    if len(snippet) < 140:
        return False
    lowered = snippet.lower()
    if any(marker in lowered for marker in _PDF_SNIPPET_FAILURE_MARKERS):
        return False
    if len(_extract_community_outcome_snippet_cues(snippet)) < 3:
        return False
    focus_overlap = set(_snippet_only_query_focus_tokens(query)) & set(
        _tokenize_scoring_text(" ".join(part for part in (candidate.title, snippet) if part))
    )
    return bool(focus_overlap)


def _extract_community_outcome_snippet_cues(snippet: str) -> tuple[str, ...]:
    lowered = snippet.lower()
    cues: list[str] = []
    for marker, canonical in _COMMUNITY_OUTCOME_SNIPPET_CUES:
        if marker in lowered and canonical not in cues:
            cues.append(canonical)
    return tuple(cues)


def _snippet_only_query_focus_tokens(query: str) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for token in _tokenize_scoring_text(query):
        if token in _QUERY_FOCUS_STOPWORDS or token in _QUERY_INTENT_MARKERS:
            continue
        if token in _SNIPPET_ONLY_QUERY_FOCUS_STOPWORDS:
            continue
        if len(token) < 3 or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return tuple(ordered)


def _meaningful_partial_pdf_scope(value: str) -> str:
    normalized = _normalize_scoring_text(value)
    if not normalized or normalized in _GENERIC_PDF_SCOPE_MARKERS:
        return ""
    return value


def _meaningful_partial_pdf_entity_match(value: str) -> str:
    normalized = _normalize_scoring_text(value)
    if not normalized:
        return ""
    if any(normalized.startswith(prefix) for prefix in _GENERIC_PDF_ENTITY_PREFIXES):
        return ""
    return value
