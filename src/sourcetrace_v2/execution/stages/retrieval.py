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
        if _query_implies_institutional_preference(query):
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
        if len(candidates) < 2 or not _query_implies_institutional_preference(query):
            return candidates
        typed = candidates if any(candidate.source_type != "unknown" for candidate in candidates) else self._annotate_source_types(candidates=candidates)
        scored: list[tuple[int, int, int, RetrievedEvidenceCandidate]] = []
        for index, candidate in enumerate(typed):
            scored.append((
                _source_mix_priority(candidate),
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
    )
    return any(marker in lowered for marker in markers)


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


def _candidate_target_quality_priority(*, candidate: RetrievedEvidenceCandidate, query: str) -> int:
    focus_tokens = _query_focus_tokens(query)
    if not focus_tokens:
        return 0
    title_tokens = set(_tokenize_scoring_text(candidate.title))
    supporting_tokens = set(
        _tokenize_scoring_text(" ".join(part for part in (candidate.snippet, candidate.url) if part))
    )
    focus_token_set = set(focus_tokens)
    title_overlap = focus_token_set & title_tokens
    supporting_overlap = focus_token_set & supporting_tokens
    normalized_candidate_text = _normalize_scoring_text(" ".join((candidate.title, candidate.snippet, candidate.url)))
    phrase_matches = sum(
        1
        for phrase in _query_focus_phrases(query)
        if phrase in normalized_candidate_text
    )
    return (len(title_overlap) * 3) + len(supporting_overlap - title_overlap) + (phrase_matches * 3)


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
    return lowered_url.endswith('.pdf') or '/pobierz,' in lowered_url or lowered_title.endswith('.pdf')
