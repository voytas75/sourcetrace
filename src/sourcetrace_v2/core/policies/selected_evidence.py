from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from sourcetrace_v2.core.contracts.compiled_artifacts import EvidenceJudgmentDimension, EvidenceJudgmentSnapshot
from sourcetrace_v2.core.domain.models import RetrievedEvidenceCandidate


AUTHORITY_RELEVANCE_JUDGMENT_CONTRACT_V1 = "authority-relevance-judgment-contract-v1"
SELECTED_EVIDENCE_SELECTION_BASIS_V1 = "rank_with_minimal_content_guard_and_domain_diversity"
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "from",
    "how",
    "into",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "when",
    "with",
}


@dataclass(frozen=True)
class SelectedEvidenceDecision:
    selected: tuple[RetrievedEvidenceCandidate, ...]
    dropped: tuple[RetrievedEvidenceCandidate, ...]
    missing_minimal_content_dropped: int
    domain_diversity_dropped: int


def _normalize_token(token: str) -> str:
    token = token.lower().strip()
    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 4 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 4 and token.endswith("ed"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def _tokenize(value: str) -> tuple[str, ...]:
    tokens = []
    for raw in _TOKEN_RE.findall(value.lower()):
        token = _normalize_token(raw)
        if len(token) < 3 or token in _STOPWORDS:
            continue
        tokens.append(token)
    return tuple(tokens)


def candidate_has_minimal_quality(candidate: RetrievedEvidenceCandidate) -> bool:
    return bool(candidate.title.strip() and candidate.url.strip() and candidate.snippet.strip())


def candidate_domain(candidate: RetrievedEvidenceCandidate) -> str:
    return urlparse(candidate.url).netloc.strip().lower()


def decide_selected_evidence(
    candidates: tuple[RetrievedEvidenceCandidate, ...],
    limit: int,
) -> SelectedEvidenceDecision:
    ordered = tuple(sorted(candidates, key=lambda candidate: candidate.rank))
    quality_candidates = tuple(candidate for candidate in ordered if candidate_has_minimal_quality(candidate))
    fallback_candidates = tuple(candidate for candidate in ordered if not candidate_has_minimal_quality(candidate))
    selected: list[RetrievedEvidenceCandidate] = []
    used_domains: set[str] = set()

    for candidate in (*quality_candidates, *fallback_candidates):
        domain = candidate_domain(candidate)
        if domain and domain not in used_domains:
            selected.append(candidate)
            used_domains.add(domain)
            if len(selected) >= limit:
                break

    if len(selected) < limit:
        for candidate in (*quality_candidates, *fallback_candidates):
            if candidate not in selected:
                selected.append(candidate)
                if len(selected) >= limit:
                    break

    chosen = tuple(selected)
    dropped = tuple(candidate for candidate in ordered if candidate not in chosen)
    selected_domains = {candidate_domain(item) for item in chosen if candidate_domain(item)}
    return SelectedEvidenceDecision(
        selected=chosen,
        dropped=dropped,
        missing_minimal_content_dropped=sum(1 for candidate in dropped if not candidate_has_minimal_quality(candidate)),
        domain_diversity_dropped=sum(
            1 for candidate in dropped if candidate_domain(candidate) in selected_domains
        ),
    )


def select_evidence_candidates(
    candidates: tuple[RetrievedEvidenceCandidate, ...],
    limit: int,
) -> tuple[tuple[RetrievedEvidenceCandidate, ...], tuple[RetrievedEvidenceCandidate, ...]]:
    decision = decide_selected_evidence(candidates, limit)
    return decision.selected, decision.dropped


def build_candidate_judgment(candidate: RetrievedEvidenceCandidate) -> EvidenceJudgmentSnapshot:
    authority = _score_authority(candidate)
    topic_match = _score_topic_match(candidate)
    specificity = _score_specificity(candidate)
    answer_fit = _score_answer_fit(authority=authority, topic_match=topic_match, specificity=specificity)
    return EvidenceJudgmentSnapshot(
        contract_version=AUTHORITY_RELEVANCE_JUDGMENT_CONTRACT_V1,
        authority=authority,
        topic_match=topic_match,
        specificity=specificity,
        answer_fit=answer_fit,
    )


def build_judgment_comparison(
    items: tuple[tuple[str, EvidenceJudgmentSnapshot], ...],
) -> dict[str, object]:
    return {
        "authority": _leaders_for(items, "authority"),
        "topic_match": _leaders_for(items, "topic_match"),
        "specificity": _leaders_for(items, "specificity"),
        "answer_fit": _leaders_for(items, "answer_fit"),
    }


def _leaders_for(
    items: tuple[tuple[str, EvidenceJudgmentSnapshot], ...],
    dimension: str,
) -> dict[str, object]:
    if not items:
        return {"top_score": 0, "leaders": []}
    scores = [(title, getattr(judgment, dimension).score) for title, judgment in items]
    top_score = max(score for _, score in scores)
    return {
        "top_score": top_score,
        "leaders": [title for title, score in scores if score == top_score],
    }


def _score_authority(candidate: RetrievedEvidenceCandidate) -> EvidenceJudgmentDimension:
    host_tokens = set(_tokenize(urlparse(candidate.url).netloc.replace(".", " ")))
    path_tokens = set(_tokenize(urlparse(candidate.url).path.replace("/", " ")))
    title_tokens = set(_tokenize(candidate.title))
    score = 0
    signals: list[str] = []

    if host_tokens & {"gov", "gouv", "government", "ministry", "agency"}:
        score = max(score, 3)
        signals.append("institutional_host")
    elif host_tokens & {"edu", "ac", "learn", "docs", "help"}:
        score = max(score, 2)
        signals.append("docs_like_host")

    if title_tokens & {"official", "institutional", "ministry", "agency"}:
        score = max(score, 2)
        signals.append("authority_title_cue")

    if (title_tokens | path_tokens) & {"faq", "guide", "reference", "policy", "manual", "baseline"}:
        score = min(3, score + 1)
        signals.append("structured_guidance_surface")

    if (host_tokens | title_tokens) & {"blog"}:
        score = max(0, score - 1)
        signals.append("blog_surface")

    return EvidenceJudgmentDimension(score=score, band=_band_for(score), signals=tuple(dict.fromkeys(signals)))


def _score_topic_match(candidate: RetrievedEvidenceCandidate) -> EvidenceJudgmentDimension:
    query_tokens = set(_tokenize(candidate.query))
    title_overlap = query_tokens & set(_tokenize(candidate.title))
    snippet_overlap = query_tokens & set(_tokenize(candidate.snippet))
    weighted_overlap = (2 * len(title_overlap)) + len(snippet_overlap)
    scale = max(1, 2 * len(query_tokens))
    ratio = weighted_overlap / scale
    score = 0
    signals: list[str] = []
    if title_overlap:
        signals.append("title_query_overlap")
    if snippet_overlap:
        signals.append("snippet_query_overlap")
    if ratio >= 0.75:
        score = 3
    elif ratio >= 0.5:
        score = 2
    elif ratio > 0:
        score = 1
    return EvidenceJudgmentDimension(score=score, band=_band_for(score), signals=tuple(signals))


def _score_specificity(candidate: RetrievedEvidenceCandidate) -> EvidenceJudgmentDimension:
    query_tokens = set(_tokenize(candidate.query))
    title_overlap = query_tokens & set(_tokenize(candidate.title))
    path_overlap = query_tokens & set(_tokenize(urlparse(candidate.url).path.replace("/", " ")))
    score = 0
    signals: list[str] = []

    if title_overlap:
        score += 1
        signals.append("focused_title_overlap")
    if len(title_overlap) >= max(2, len(query_tokens) // 2):
        score += 1
        signals.append("dense_title_overlap")
    if path_overlap:
        score += 1
        signals.append("focused_url_path")

    score = min(score, 3)
    return EvidenceJudgmentDimension(score=score, band=_band_for(score), signals=tuple(signals))


def _score_answer_fit(
    *,
    authority: EvidenceJudgmentDimension,
    topic_match: EvidenceJudgmentDimension,
    specificity: EvidenceJudgmentDimension,
) -> EvidenceJudgmentDimension:
    weighted_total = authority.score + (2 * topic_match.score) + (2 * specificity.score)
    ratio = weighted_total / 15
    score = 0
    if ratio >= 0.75:
        score = 3
    elif ratio >= 0.5:
        score = 2
    elif ratio > 0:
        score = 1
    signals = []
    if authority.score:
        signals.append("authority_contributes")
    if topic_match.score:
        signals.append("topic_match_contributes")
    if specificity.score:
        signals.append("specificity_contributes")
    return EvidenceJudgmentDimension(score=score, band=_band_for(score), signals=tuple(signals))


def _band_for(score: int) -> str:
    return {
        0: "none",
        1: "low",
        2: "medium",
        3: "high",
    }.get(score, "none")
