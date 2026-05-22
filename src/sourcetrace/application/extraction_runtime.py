"""Minimal application runtime for LLM-backed claim extraction."""

from os import environ
from typing import TYPE_CHECKING
import json
import re

from sourcetrace.application.extraction import ClaimExtractionOutcome, ClaimExtractionRequest
from sourcetrace.domain import Claim, ClaimEvidenceLink, Document, DocumentChunk
from sourcetrace.domain.types import VerificationVerdict

if TYPE_CHECKING:
    from sourcetrace.llm.interfaces import ClaimExtractionGateway, ClaimNormalizationGateway
    from sourcetrace.storage.interfaces import ClaimRepository


_CLAIM_TEXT_KEYS = ("exact_text", "text", "claim", "statement", "claim_text")
_CLAIM_CHUNK_KEYS = ("chunk_id", "source_chunk_id", "chunk")
_SPAN_REFERENCE_KEYS = ("source_span_reference", "span_reference", "span")
_EVIDENCE_KEYS = ("evidence", "evidence_items", "supporting_evidence")
_EVIDENCE_CHUNK_KEYS = ("chunk_id", "source_chunk_id", "chunk")
_EVIDENCE_SNIPPET_KEYS = ("snippet", "text", "quote", "evidence")
_EVIDENCE_RATIONALE_KEYS = ("rationale", "reason", "explanation")
_PERCENT_VALUE_PATTERN = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*(?:%|percent(?:age)?\b|per cent\b)",
    re.IGNORECASE,
)
_CONVERSATIONAL_CLAIM_PATTERNS = (
    "could you please clarify",
    "could you clarify",
    "if you need help",
    "let me know and i can help",
    "let me know and i can assist",
    "let me know if you need help",
    "let me know if you need",
    "thank you for your update",
    "thank you for the update",
    "it looks like you mentioned",
    "let me know how i can assist",
    "please provide more context",
    "so i can assist you better",
    "are you asking for more details",
    "here are a few ways you might do so",
    "if you need to expand or clarify this statement",
    "help drafting a report, summary, or announcement",
    "glad to hear",
    "i can help you draft",
    "customer notice",
    "incident summary",
    "outage update",
    "yes —",
    "yes -",
    "yes, ",
    "no —",
    "no -",
    "no, ",
)
_SUBORDINATE_CLAUSE_CONTENT_TOKEN_STOP_WORDS = frozenset(
    (
        "a",
        "an",
        "and",
        "are",
        "as",
        "be",
        "been",
        "being",
        "but",
        "by",
        "can",
        "could",
        "despite",
        "did",
        "do",
        "does",
        "even",
        "for",
        "from",
        "had",
        "has",
        "have",
        "however",
        "if",
        "in",
        "is",
        "it",
        "may",
        "might",
        "of",
        "only",
        "or",
        "prove",
        "proved",
        "proves",
        "remain",
        "remained",
        "remains",
        "said",
        "say",
        "saying",
        "says",
        "should",
        "that",
        "the",
        "though",
        "to",
        "was",
        "were",
        "while",
        "will",
        "with",
    )
)
_SUBORDINATE_CLAUSE_CONTENT_TOKEN_ALIASES = {
    "analysts": "analyst",
    "costs": "cost",
    "eased": "ease",
    "eases": "ease",
    "easing": "ease",
    "economists": "economist",
    "increases": "increase",
    "prices": "price",
    "temporarily": "temporary",
}
_CONTEXTUAL_CLAIM_CONNECTOR_PATTERNS = (
    re.compile(r"\bwhile\s+[^,.;:]+\b(?:said|saying|says)\b", re.IGNORECASE),
    re.compile(r"\bdespite\s+[^,.;:]+\b(?:said|saying|says)\b", re.IGNORECASE),
    re.compile(r"\balthough\s+[^,.;:]+\b(?:said|saying|says)\b", re.IGNORECASE),
    re.compile(r"\bthough\s+[^,.;:]+\b(?:said|saying|says)\b", re.IGNORECASE),
    re.compile(r"\bhowever,?\s+[^.]+\b(?:said|saying|says)\b", re.IGNORECASE),
)
_CLAIM_ROLE_CORE_FACT = "core_fact"
_CLAIM_ROLE_CONTEXTUAL_CARRY_THROUGH = "contextual_carry_through"
_CLAIM_ROLE_SUBORDINATE_ATTRIBUTION = "subordinate_attribution"
_CLAIM_TYPE_ROLES = {
    "attributed_statement": _CLAIM_ROLE_SUBORDINATE_ATTRIBUTION,
    "causal": _CLAIM_ROLE_CORE_FACT,
    "causal_statement": _CLAIM_ROLE_CORE_FACT,
    "fact": _CLAIM_ROLE_CORE_FACT,
    "factual": _CLAIM_ROLE_CORE_FACT,
    "factual_statement": _CLAIM_ROLE_CORE_FACT,
}


def _claim_debug_enabled() -> bool:
    return environ.get("SOURCETRACE_DEBUG_CLAIM_PIPELINE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _safe_debug_preview(value: object, *, limit: int = 1200) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        text = repr(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}…"


def _debug_claim_pipeline_stage(*, stage: str, payload: object) -> None:
    if not _claim_debug_enabled():
        return
    print(
        "[sourcetrace.claim-debug] "
        f"stage={stage} "
        f"payload_type={type(payload).__name__} "
        f"payload_preview={_safe_debug_preview(payload)!r}",
        flush=True,
    )


class _LlmClaimExtractor:
    def __init__(
        self,
        *,
        extract_claims: "ClaimExtractionGateway",
        normalize_claim: "ClaimNormalizationGateway | None" = None,
        claim_repository: "ClaimRepository | None" = None,
    ) -> None:
        self._extract_claims = extract_claims
        self._normalize_claim = normalize_claim
        self._claim_repository = claim_repository

    def __call__(
        self,
        request: ClaimExtractionRequest,
        *,
        document: Document,
        chunks: tuple[DocumentChunk, ...],
    ) -> ClaimExtractionOutcome:
        chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        prepared_text = "\n\n".join(
            f"[{chunk.chunk_id}] {chunk.raw_text}"
            for chunk in chunks
            if chunk.chunk_id in request.chunk_ids
        )
        result = self._extract_claims(prepared_text)
        _debug_claim_pipeline_stage(stage="raw_payload", payload=result.payload)
        claim_items, dropped_claim_items = _claim_items_for(result.payload)
        _debug_claim_pipeline_stage(stage="claim_items_for", payload=claim_items)
        claim_items = _deduplicate_claim_items(claim_items)
        _debug_claim_pipeline_stage(stage="deduplicated_claim_items", payload=claim_items)
        claims = tuple(
            Claim(
                claim_id=(
                    _normalized_string(item.get("claim_id"))
                    or f"{request.case_id}:claim-{index + 1}"
                ),
                case_id=request.case_id,
                document_id=request.document_id,
                chunk_id=_chunk_id_for(
                    item=item,
                    request=request,
                    chunk_by_id=chunk_by_id,
                ),
                exact_text=_claim_text_for(
                    item=item,
                    normalize_claim=self._normalize_claim,
                    source_language=_prepared_text_language(chunks),
                ),
                source_span_reference=_span_reference_for(
                    item=item,
                    request=request,
                    chunk_by_id=chunk_by_id,
                ),
                system_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
                rationale=None,
            )
            for index, item in enumerate(claim_items)
        )
        if self._claim_repository is not None:
            claims = self._claim_repository.save_claims(claims)
        evidence_links = _build_initial_evidence_links(
            claims=claims,
            items=claim_items,
        )
        dropped_evidence_items = _count_dropped_evidence_items(claim_items)
        if self._claim_repository is not None:
            evidence_links = self._claim_repository.save_evidence_links(evidence_links)
        return ClaimExtractionOutcome(
            request=request,
            document=document,
            chunks=chunks,
            claims=claims,
            evidence_links=evidence_links,
            dropped_claim_items=dropped_claim_items,
            dropped_evidence_items=dropped_evidence_items,
        )


def _chunk_id_for(
    item: dict[str, object],
    request: ClaimExtractionRequest,
    *,
    chunk_by_id: dict[str, DocumentChunk],
) -> str | None:
    chunk_id = _first_normalized_item_string(item, *_CLAIM_CHUNK_KEYS)
    if chunk_id is not None:
        return chunk_id
    inferred_chunk = _infer_chunk_from_claim_text(
        claim_text=_first_normalized_item_string(item, *_CLAIM_TEXT_KEYS),
        request=request,
        chunk_by_id=chunk_by_id,
    )
    if inferred_chunk is not None:
        return inferred_chunk.chunk_id
    if request.chunk_ids:
        return request.chunk_ids[0]
    return None


def _normalized_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def _claim_text_for(
    *,
    item: dict[str, object],
    normalize_claim: "ClaimNormalizationGateway | None",
    source_language: str | None,
) -> str:
    exact_text = _first_normalized_item_string(item, *_CLAIM_TEXT_KEYS) or ""
    if normalize_claim is None or not exact_text:
        return exact_text
    normalized = normalize_claim(exact_text).text.strip()
    if _looks_conversational_response(normalized):
        return exact_text
    if _drops_attribution_or_caveat(source_text=exact_text, normalized_text=normalized):
        return exact_text
    if _changes_percentage_value(source_text=exact_text, normalized_text=normalized):
        return exact_text
    if _looks_like_cross_language_drift(
        source_text=exact_text,
        normalized_text=normalized,
        source_language=source_language,
    ):
        return exact_text
    return normalized or exact_text


def _prepared_text_language(chunks: tuple[DocumentChunk, ...]) -> str | None:
    sample = "\n".join(chunk.raw_text for chunk in chunks if chunk.raw_text).strip()
    if not sample:
        return None
    lowered = sample.casefold()
    polish_markers = (
        " że ",
        " się ",
        " oraz ",
        " został ",
        " została ",
        " przez ",
        " roku ",
        " miasto ",
        " program ",
        " pojazd",
        " autobus",
    )
    if any(marker in f" {lowered} " for marker in polish_markers):
        return "pl"
    if re.search(r"[ąćęłńóśźż]", lowered):
        return "pl"
    return None


def _looks_like_cross_language_drift(
    *,
    source_text: str,
    normalized_text: str,
    source_language: str | None,
) -> bool:
    if source_language != "pl":
        return False
    if not normalized_text:
        return False
    if re.search(r"[ąćęłńóśźż]", normalized_text.casefold()):
        return False
    english_markers = (
        " the ",
        " there is ",
        " there are ",
        " according to ",
        " at the ",
        " on the ",
        " in the ",
        " disclaimer",
        " study",
        " page",
        " bottom",
    )
    normalized_padded = f" {normalized_text.casefold()} "
    source_padded = f" {source_text.casefold()} "
    english_hits = sum(1 for marker in english_markers if marker in normalized_padded)
    if english_hits == 0:
        return False
    polish_hits_in_source = sum(
        1
        for marker in (" że ", " się ", " oraz ", " jest ", " zosta", " badan", " stroni")
        if marker in source_padded
    )
    return polish_hits_in_source > 0


def _drops_attribution_or_caveat(*, source_text: str, normalized_text: str) -> bool:
    source = source_text.casefold()
    normalized = normalized_text.casefold()
    for marker in (
        " said ",
        " according to ",
        " warned ",
        " claimed ",
        " stated ",
        " reported ",
        " analysts ",
        " analyst ",
        " ministry ",
        " agency ",
        " central bank",
        " should not be treated as",
        " remain temporary",
        " remains temporary",
        " no implementation timetable",
        " but ",
        " however ",
        " although ",
        " despite ",
        " no dataset",
        " no evidence",
        " has not been published",
        " has not been released",
    ):
        if marker in source and marker not in normalized:
            return True
    return False


def _changes_percentage_value(*, source_text: str, normalized_text: str) -> bool:
    source_values = _percentage_values(source_text)
    if not source_values:
        return False
    return source_values != _percentage_values(normalized_text)


def _percentage_values(text: str) -> tuple[str, ...]:
    values: list[str] = []
    for match in _PERCENT_VALUE_PATTERN.finditer(text):
        value = match.group(1).replace(",", ".")
        if "." in value:
            value = value.rstrip("0").rstrip(".")
        values.append(value.lstrip("0") or "0")
    return tuple(values)


def _normalized_item_string(item: dict[str, object], key: str) -> str | None:
    return _normalized_string(item.get(key))


def _first_normalized_item_string(item: dict[str, object], *keys: str) -> str | None:
    for key in keys:
        normalized = _normalized_item_string(item, key)
        if normalized is not None:
            return normalized
    return None


def _has_any_normalized_string(item: dict[str, object], *keys: str) -> bool:
    return any(_normalized_item_string(item, key) is not None for key in keys)


def _claim_items_for(payload: dict[str, object]) -> tuple[tuple[dict[str, object], ...], int]:
    claims = payload.get("claims")
    if not isinstance(claims, list):
        return (), 0
    normalized = tuple(item for item in claims if _is_valid_claim_payload(item))
    return normalized, len(claims) - len(normalized)


def _deduplicate_claim_items(
    items: tuple[dict[str, object], ...],
) -> tuple[dict[str, object], ...]:
    source_texts = _claim_item_bundle_source_texts(items)
    deduplicated: list[dict[str, object]] = []
    for item in items:
        claim_text = _first_normalized_item_string(item, *_CLAIM_TEXT_KEYS)
        if claim_text is None:
            deduplicated.append(item)
            continue
        for index, existing in enumerate(deduplicated):
            existing_text = _first_normalized_item_string(existing, *_CLAIM_TEXT_KEYS)
            if existing_text is None:
                continue
            duplicate_resolution = _resolve_duplicate_claim_item(
                existing=existing,
                existing_text=existing_text,
                candidate=item,
                candidate_text=claim_text,
            )
            if duplicate_resolution is None:
                continue
            if duplicate_resolution is item:
                deduplicated[index] = item
            break
        else:
            deduplicated.append(item)
    return _apply_role_based_claim_bundle_policy(
        tuple(deduplicated),
        source_texts=source_texts,
    )


def _claim_item_bundle_source_texts(
    items: tuple[dict[str, object], ...],
) -> tuple[str, ...]:
    source_texts: list[str] = []
    seen: set[str] = set()
    for item in items:
        candidate_texts = [
            text
            for text in (
                _first_normalized_item_string(item, *_CLAIM_TEXT_KEYS),
                *(
                    _first_normalized_item_string(evidence, *_EVIDENCE_SNIPPET_KEYS)
                    for evidence in _evidence_items_for(item)
                ),
            )
            if text is not None
        ]
        for candidate_text in candidate_texts:
            for source_text in _source_sentence_spans(candidate_text):
                normalized = _normalized_claim_text_for_subsequence(source_text)
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                source_texts.append(source_text)
    return tuple(source_texts)


def _resolve_duplicate_claim_item(
    *,
    existing: dict[str, object],
    existing_text: str,
    candidate: dict[str, object],
    candidate_text: str,
) -> dict[str, object] | None:
    if _is_carry_through_duplicate_claim_text(existing_text, candidate_text):
        return _prefer_core_fact_claim_item(
            left=existing,
            left_text=existing_text,
            right=candidate,
            right_text=candidate_text,
        )
    if _is_near_duplicate_claim_text(existing_text, candidate_text):
        if len(candidate_text) > len(existing_text):
            return candidate
        return existing
    return None


def _apply_role_based_claim_bundle_policy(
    items: tuple[dict[str, object], ...],
    *,
    source_texts: tuple[str, ...],
) -> tuple[dict[str, object], ...]:
    item_texts = tuple(
        _first_normalized_item_string(item, *_CLAIM_TEXT_KEYS) or "" for item in items
    )
    item_roles = tuple(
        _claim_item_role(item=item, text=item_text)
        for item, item_text in zip(items, item_texts, strict=True)
    )
    dropped_indices: set[int] = set()
    for bundle_indices in _claim_item_bundle_index_groups(
        items=items,
        item_texts=item_texts,
        item_roles=item_roles,
        source_texts=source_texts,
    ):
        bundle_roles = {item_roles[index] for index in bundle_indices}
        if _CLAIM_ROLE_CORE_FACT in bundle_roles:
            dropped_indices.update(
                index
                for index in bundle_indices
                if item_roles[index]
                in (
                    _CLAIM_ROLE_CONTEXTUAL_CARRY_THROUGH,
                    _CLAIM_ROLE_SUBORDINATE_ATTRIBUTION,
                )
            )
            continue
        if _CLAIM_ROLE_CONTEXTUAL_CARRY_THROUGH in bundle_roles:
            dropped_indices.update(
                index
                for index in bundle_indices
                if item_roles[index] == _CLAIM_ROLE_SUBORDINATE_ATTRIBUTION
            )
    if not dropped_indices:
        return items
    return tuple(item for index, item in enumerate(items) if index not in dropped_indices)


def _claim_item_bundle_index_groups(
    *,
    items: tuple[dict[str, object], ...],
    item_texts: tuple[str, ...],
    item_roles: tuple[str, ...],
    source_texts: tuple[str, ...],
) -> tuple[tuple[int, ...], ...]:
    if len(items) < 2:
        return ()
    parents = list(range(len(items)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    for left_index in range(len(items)):
        for right_index in range(left_index + 1, len(items)):
            if _claim_items_are_bundle_related(
                left=items[left_index],
                left_text=item_texts[left_index],
                left_role=item_roles[left_index],
                right=items[right_index],
                right_text=item_texts[right_index],
                right_role=item_roles[right_index],
                source_texts=source_texts,
            ):
                union(left_index, right_index)

    groups_by_root: dict[int, list[int]] = {}
    for index in range(len(items)):
        groups_by_root.setdefault(find(index), []).append(index)
    return tuple(
        tuple(group)
        for group in groups_by_root.values()
        if len(group) > 1
    )


def _claim_items_are_bundle_related(
    *,
    left: dict[str, object],
    left_text: str,
    left_role: str,
    right: dict[str, object],
    right_text: str,
    right_role: str,
    source_texts: tuple[str, ...],
) -> bool:
    if not left_text or not right_text:
        return False
    if left_role == right_role == _CLAIM_ROLE_CORE_FACT:
        return False
    if _roles_match(
        left_role,
        right_role,
        _CLAIM_ROLE_CORE_FACT,
        _CLAIM_ROLE_CONTEXTUAL_CARRY_THROUGH,
    ):
        return _is_carry_through_duplicate_claim_text(left_text, right_text)
    if _roles_match(
        left_role,
        right_role,
        _CLAIM_ROLE_CONTEXTUAL_CARRY_THROUGH,
        _CLAIM_ROLE_SUBORDINATE_ATTRIBUTION,
    ):
        carry_text, subordinate_text = _texts_by_role(
            left_text=left_text,
            left_role=left_role,
            right_text=right_text,
            right_role=right_role,
            role=_CLAIM_ROLE_CONTEXTUAL_CARRY_THROUGH,
        )
        return _contains_subordinate_clause_text(
            container_text=carry_text,
            subordinate_text=subordinate_text,
        )
    if _roles_match(
        left_role,
        right_role,
        _CLAIM_ROLE_CORE_FACT,
        _CLAIM_ROLE_SUBORDINATE_ATTRIBUTION,
    ):
        core_text, subordinate_text = _texts_by_role(
            left_text=left_text,
            left_role=left_role,
            right_text=right_text,
            right_role=right_role,
            role=_CLAIM_ROLE_CORE_FACT,
        )
        return _has_claim_bundle_source_bridge(
            core_text=core_text,
            subordinate_text=subordinate_text,
            source_texts=source_texts,
        )
    return False


def _roles_match(left_role: str, right_role: str, first_role: str, second_role: str) -> bool:
    return {left_role, right_role} == {first_role, second_role}


def _texts_by_role(
    *,
    left_text: str,
    left_role: str,
    right_text: str,
    right_role: str,
    role: str,
) -> tuple[str, str]:
    if left_role == role:
        return left_text, right_text
    if right_role == role:
        return right_text, left_text
    return left_text, right_text


def _has_claim_bundle_source_bridge(
    *,
    core_text: str,
    subordinate_text: str,
    source_texts: tuple[str, ...],
) -> bool:
    return any(
        _is_carry_through_context_claim_text(source_text)
        and _contains_subordinate_clause_text(
            container_text=source_text,
            subordinate_text=subordinate_text,
        )
        and _is_carry_through_duplicate_claim_text(core_text, source_text)
        for source_text in source_texts
    )


def _claim_text_role(text: str) -> str:
    if _is_carry_through_context_claim_text(text):
        return _CLAIM_ROLE_CONTEXTUAL_CARRY_THROUGH
    if _is_subordinate_clause_claim_text(text):
        return _CLAIM_ROLE_SUBORDINATE_ATTRIBUTION
    return _CLAIM_ROLE_CORE_FACT


def _claim_item_role(*, item: dict[str, object], text: str) -> str:
    payload_type_role = _claim_payload_type_role(item.get("type"))
    if payload_type_role is not None:
        return payload_type_role
    return _claim_text_role(text)


def _claim_payload_type_role(value: object) -> str | None:
    claim_type = _normalized_claim_payload_type(value)
    if claim_type is None:
        return None
    return _CLAIM_TYPE_ROLES.get(claim_type)


def _normalized_claim_payload_type(value: object) -> str | None:
    normalized = _normalized_string(value)
    if normalized is None:
        return None
    return re.sub(r"[\s-]+", "_", normalized.casefold())


def _contains_subordinate_clause_text(*, container_text: str, subordinate_text: str) -> bool:
    container = _normalized_claim_text_for_subsequence(container_text)
    subordinate = _normalized_claim_text_for_subsequence(subordinate_text)
    if not container or not subordinate:
        return False
    if subordinate in container:
        return True
    return _has_subordinate_clause_content_coverage(
        container_text=container_text,
        subordinate_text=subordinate_text,
    )


def _has_subordinate_clause_content_coverage(
    *,
    container_text: str,
    subordinate_text: str,
) -> bool:
    container_tokens = set(_subordinate_clause_content_tokens(container_text))
    subordinate_tokens = set(_subordinate_clause_content_tokens(subordinate_text))
    if len(subordinate_tokens) < 3:
        return False
    shared_tokens = subordinate_tokens & container_tokens
    return (
        len(shared_tokens) >= 3
        and len(shared_tokens) / len(subordinate_tokens) >= 0.67
    )


def _subordinate_clause_content_tokens(text: str) -> tuple[str, ...]:
    return tuple(
        canonical_token
        for raw_token in re.findall(r"\w+", text.casefold())
        if (
            canonical_token := _canonical_subordinate_clause_content_token(raw_token)
        )
        is not None
    )


def _canonical_subordinate_clause_content_token(token: str) -> str | None:
    canonical = _SUBORDINATE_CLAUSE_CONTENT_TOKEN_ALIASES.get(token, token)
    if canonical in _SUBORDINATE_CLAUSE_CONTENT_TOKEN_STOP_WORDS:
        return None
    if len(canonical) < 3:
        return None
    return canonical


def _is_core_fact_claim_text(text: str) -> bool:
    return not _is_subordinate_clause_claim_text(text) and not _is_carry_through_context_claim_text(
        text
    )


def _is_carry_through_context_claim_text(text: str) -> bool:
    if any(pattern.search(text) for pattern in _CONTEXTUAL_CLAIM_CONNECTOR_PATTERNS):
        return True
    normalized = f" {_normalized_claim_text_for_subsequence(text)} "
    return any(
        marker in normalized
        for marker in (
            " while ",
            " despite ",
            " though ",
            " even though ",
            " however ",
            " although ",
            " but ",
        )
    )


def _is_subordinate_clause_claim_text(text: str) -> bool:
    normalized = f" {_normalized_claim_text_for_subsequence(text)} "
    return any(
        marker in normalized
        for marker in (
            " economists said ",
            " economist said ",
            " analysts said ",
            " analyst said ",
            " bank of england has said ",
            " has said ",
            " warned ",
            " according to ",
            " said the increase may ",
            " saying ",
        )
    )


def _is_carry_through_duplicate_claim_text(left: str, right: str) -> bool:
    left_normalized = _normalized_claim_text_for_subsequence(left)
    right_normalized = _normalized_claim_text_for_subsequence(right)
    if left_normalized in right_normalized:
        shorter_text, longer_text = left, right
    elif right_normalized in left_normalized:
        shorter_text, longer_text = right, left
    else:
        return False
    trailing_text = _carry_through_suffix(longer_text, shorter_text)
    if trailing_text is None:
        return False
    return _looks_like_carry_through_suffix(trailing_text)


def _normalized_claim_text_for_subsequence(text: str) -> str:
    return re.sub(r"[^\w]+", " ", text.casefold()).strip()


def _carry_through_suffix(longer_text: str, shorter_text: str) -> str | None:
    longer_normalized = longer_text.strip()
    shorter_normalized = shorter_text.strip().rstrip(".?!")
    if not shorter_normalized:
        return None
    prefix_index = longer_normalized.casefold().find(shorter_normalized.casefold())
    if prefix_index != 0:
        return None
    suffix = longer_normalized[len(shorter_normalized) :].strip()
    if not suffix:
        return None
    return suffix


def _looks_like_carry_through_suffix(text: str) -> bool:
    normalized = text.casefold().strip()
    normalized = normalized.lstrip(",;:—- ")
    if not normalized:
        return False
    return normalized.startswith((
        "but ",
        "however ",
        "however, ",
        "although ",
        "if ",
        "while ",
        "though ",
        "even though ",
        "despite ",
        "despite the fact that ",
    ))


def _prefer_core_fact_claim_item(
    *,
    left: dict[str, object],
    left_text: str,
    right: dict[str, object],
    right_text: str,
) -> dict[str, object]:
    if len(_normalized_claim_text_for_subsequence(left_text)) <= len(
        _normalized_claim_text_for_subsequence(right_text)
    ):
        return left
    return right


def _is_near_duplicate_claim_text(left: str, right: str) -> bool:
    left_tokens = _claim_text_tokens(left)
    right_tokens = _claim_text_tokens(right)
    if not left_tokens or not right_tokens:
        return False
    shorter, longer = (left_tokens, right_tokens)
    if len(shorter) > len(longer):
        shorter, longer = longer, shorter
    overlap = sum(1 for token in shorter if token in longer)
    return overlap / len(shorter) >= 0.9


def _claim_text_tokens(text: str) -> tuple[str, ...]:
    return tuple(
        token
        for token in (
            normalized.strip(".,;:!?()[]{}\"'")
            for normalized in text.casefold().split()
        )
        if token
    )


def _is_valid_claim_payload(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    if _is_conversational_claim_payload(item):
        return False
    return _has_any_normalized_string(
        item,
        "claim_id",
        *_CLAIM_CHUNK_KEYS,
        *_CLAIM_TEXT_KEYS,
        *_SPAN_REFERENCE_KEYS,
    ) or bool(_evidence_items_for(item))


def _is_conversational_claim_payload(item: dict[str, object]) -> bool:
    claim_text = _first_normalized_item_string(item, *_CLAIM_TEXT_KEYS)
    if claim_text is None:
        return False
    return _looks_conversational_response(claim_text)


def _looks_conversational_response(text: str) -> bool:
    normalized = text.casefold()
    if any(pattern in normalized for pattern in _CONVERSATIONAL_CLAIM_PATTERNS):
        return True
    if "if you want" in normalized and "i can help" in normalized:
        return True
    if any(
        marker in normalized
        for marker in (
            "status update",
            "draft a report",
            "draft an update",
            "draft a status update",
            "customer notice",
            "incident summary",
        )
    ) and any(
        marker in normalized
        for marker in (
            "i can help",
            "i can assist",
            "if you want",
            "let me know",
        )
    ):
        return True
    line_count = sum(1 for line in text.splitlines() if line.strip())
    if line_count >= 3:
        return True
    if any(marker in normalized for marker in ("if you'd like", "if you would like", "let me know", "here's a bit more context", "to elaborate", "summary:")):
        return True
    if text.count("**") >= 2:
        return True
    return False


def _span_reference_for(
    *,
    item: dict[str, object],
    request: ClaimExtractionRequest,
    chunk_by_id: dict[str, DocumentChunk],
) -> str:
    span_reference = _first_normalized_item_string(item, *_SPAN_REFERENCE_KEYS)
    if span_reference is not None:
        return span_reference
    chunk_id = _first_normalized_item_string(item, *_CLAIM_CHUNK_KEYS)
    if chunk_id is not None:
        chunk = chunk_by_id.get(chunk_id)
        if chunk is not None and chunk.position_reference is not None:
            return chunk.position_reference
    inferred_chunk = _infer_chunk_from_claim_text(
        claim_text=_first_normalized_item_string(item, *_CLAIM_TEXT_KEYS),
        request=request,
        chunk_by_id=chunk_by_id,
    )
    if inferred_chunk is not None and inferred_chunk.position_reference is not None:
        return inferred_chunk.position_reference
    if len(request.chunk_ids) == 1:
        request_chunk = chunk_by_id.get(request.chunk_ids[0])
        if request_chunk is not None and request_chunk.position_reference is not None:
            return request_chunk.position_reference
    return "chunk-span:unknown"


def _infer_chunk_from_claim_text(
    *,
    claim_text: str | None,
    request: ClaimExtractionRequest,
    chunk_by_id: dict[str, DocumentChunk],
) -> DocumentChunk | None:
    normalized_claim = _normalized_string(claim_text)
    if normalized_claim is None:
        return None
    candidate_chunks = tuple(
        chunk
        for chunk_id in request.chunk_ids
        if (chunk := chunk_by_id.get(chunk_id)) is not None
    )
    matches: list[DocumentChunk] = []
    normalized_claim_folded = normalized_claim.casefold()
    for chunk in candidate_chunks:
        raw_text = _normalized_string(chunk.raw_text)
        if raw_text is None:
            continue
        if normalized_claim_folded in raw_text.casefold():
            matches.append(chunk)
    if len(matches) == 1:
        return matches[0]
    return _infer_chunk_from_claim_similarity(
        claim_text=normalized_claim,
        candidate_chunks=candidate_chunks,
    )


def _infer_chunk_from_claim_similarity(
    *,
    claim_text: str,
    candidate_chunks: tuple[DocumentChunk, ...],
) -> DocumentChunk | None:
    claim_terms = _match_terms(claim_text)
    if len(claim_terms) < 4:
        return None
    scored_candidates: list[tuple[float, int, DocumentChunk]] = []
    for chunk in candidate_chunks:
        raw_text = _normalized_string(chunk.raw_text)
        if raw_text is None:
            continue
        similarity = _best_chunk_similarity(claim_terms=claim_terms, raw_text=raw_text)
        if similarity is None:
            continue
        score, shared_term_count = similarity
        scored_candidates.append((score, shared_term_count, chunk))
    if not scored_candidates:
        return None
    scored_candidates.sort(
        key=lambda entry: (
            entry[0],
            entry[1],
            _is_heading_like_chunk(entry[2]),
            -entry[2].chunk_index,
        ),
        reverse=True,
    )
    score, shared_term_count, chunk = scored_candidates[0]
    if score < 0.6:
        return None
    if len(scored_candidates) > 1:
        runner_up = scored_candidates[1]
        if _similarity_candidates_are_ambiguous(
            best=(score, shared_term_count, chunk),
            runner_up=runner_up,
        ):
            return None
    return chunk


def _similarity_candidates_are_ambiguous(
    *,
    best: tuple[float, int, DocumentChunk],
    runner_up: tuple[float, int, DocumentChunk],
) -> bool:
    best_score, best_shared_term_count, best_chunk = best
    runner_up_score, runner_up_shared_term_count, runner_up_chunk = runner_up
    if best_score - runner_up_score >= 0.1:
        return False
    if best_shared_term_count - runner_up_shared_term_count >= 2:
        return False
    if _is_heading_like_chunk(best_chunk) and not _is_heading_like_chunk(runner_up_chunk):
        return True
    if not _is_heading_like_chunk(best_chunk) and _is_heading_like_chunk(runner_up_chunk):
        return False
    return True


def _is_heading_like_chunk(chunk: DocumentChunk) -> bool:
    raw_text = _normalized_string(chunk.raw_text)
    if raw_text is None:
        return False
    if len(raw_text) <= 140 and raw_text.lstrip().startswith("#"):
        return True
    return False


def _best_chunk_similarity(
    *,
    claim_terms: set[str],
    raw_text: str,
) -> tuple[float, int] | None:
    best_similarity: tuple[float, int] | None = None
    for chunk_terms in _chunk_match_term_sets(raw_text):
        if len(chunk_terms) < 4:
            continue
        shared_terms = claim_terms & chunk_terms
        if len(shared_terms) < 4:
            continue
        claim_coverage = len(shared_terms) / len(claim_terms)
        if claim_coverage < 0.75:
            continue
        chunk_coverage = len(shared_terms) / len(chunk_terms)
        similarity = (min(claim_coverage, chunk_coverage), len(shared_terms))
        if best_similarity is None or similarity > best_similarity:
            best_similarity = similarity
    return best_similarity


def _chunk_match_term_sets(text: str) -> tuple[set[str], ...]:
    term_sets: list[set[str]] = []
    seen: set[frozenset[str]] = set()
    for span_text in (*_source_sentence_spans(text), text):
        terms = _match_terms(span_text)
        frozen_terms = frozenset(terms)
        if not terms or frozen_terms in seen:
            continue
        seen.add(frozen_terms)
        term_sets.append(terms)
    return tuple(term_sets)


def _source_sentence_spans(text: str) -> tuple[str, ...]:
    return tuple(
        span.strip()
        for span in re.split(r"(?<=[.!?])\s+|\n+", text)
        if span.strip()
    )


def _match_terms(text: str) -> set[str]:
    return {
        term
        for term in re.split(r"[^\w]+", text.casefold())
        if len(term) >= 4
    }


def _build_initial_evidence_links(
    *,
    claims: tuple[Claim, ...],
    items: tuple[dict[str, object], ...],
) -> tuple[ClaimEvidenceLink, ...]:
    evidence_links: list[ClaimEvidenceLink] = []
    for claim, item in zip(claims, items, strict=False):
        evidence_links.extend(_build_initial_evidence_links_for_claim(claim=claim, item=item))
    return tuple(evidence_links)


def _build_initial_evidence_links_for_claim(
    *,
    claim: Claim,
    item: dict[str, object],
) -> tuple[ClaimEvidenceLink, ...]:
    evidence_items = _evidence_items_for(item)
    if not evidence_items:
        return (_build_initial_evidence_link(claim=claim, evidence_payload={}, evidence_rank=1),)
    return tuple(
        _build_initial_evidence_link(
            claim=claim,
            evidence_payload=evidence_payload,
            evidence_rank=index,
        )
        for index, evidence_payload in enumerate(evidence_items, start=1)
    )


def _count_dropped_evidence_items(items: tuple[dict[str, object], ...]) -> int:
    return sum(_dropped_evidence_items_for(item) for item in items)


def _dropped_evidence_items_for(item: dict[str, object]) -> int:
    evidence = _evidence_payload_for(item)
    if isinstance(evidence, dict) or not isinstance(evidence, list):
        return 0
    return len(evidence) - len(_evidence_items_for(item))


def _build_initial_evidence_link(
    *,
    claim: Claim,
    evidence_payload: dict[str, object],
    evidence_rank: int,
) -> ClaimEvidenceLink:
    span_reference = claim.source_span_reference or "chunk-span:unknown"
    return ClaimEvidenceLink(
        claim_id=claim.claim_id,
        document_id=claim.document_id,
        chunk_id=_evidence_chunk_id(evidence_payload, claim=claim),
        evidence_rank=evidence_rank,
        evidence_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        rationale=_evidence_rationale(evidence_payload, span_reference=span_reference),
        snippet=_evidence_snippet(evidence_payload, claim=claim),
        score=_evidence_score(evidence_payload),
    )


def _evidence_items_for(item: dict[str, object]) -> tuple[dict[str, object], ...]:
    evidence = _evidence_payload_for(item)
    if isinstance(evidence, dict):
        return (evidence,)
    if not isinstance(evidence, list):
        return ()
    return tuple(entry for entry in evidence if _is_valid_evidence_payload(entry))


def _evidence_payload_for(item: dict[str, object]) -> object:
    for key in _EVIDENCE_KEYS:
        evidence = item.get(key)
        if isinstance(evidence, dict | list):
            return evidence
    return None


def _is_valid_evidence_payload(entry: object) -> bool:
    if not isinstance(entry, dict):
        return False
    return _has_any_normalized_string(
        entry,
        *_EVIDENCE_CHUNK_KEYS,
        *_EVIDENCE_SNIPPET_KEYS,
        *_EVIDENCE_RATIONALE_KEYS,
    ) or isinstance(
        entry.get("score"),
        int | float,
    )


def _evidence_chunk_id(
    evidence_payload: dict[str, object],
    *,
    claim: Claim,
) -> str | None:
    chunk_id = _first_normalized_item_string(evidence_payload, *_EVIDENCE_CHUNK_KEYS)
    if chunk_id is not None:
        return chunk_id
    return claim.chunk_id


def _evidence_rationale(
    evidence_payload: dict[str, object],
    *,
    span_reference: str,
) -> str:
    rationale = _first_normalized_item_string(evidence_payload, *_EVIDENCE_RATIONALE_KEYS)
    if rationale is not None:
        return rationale
    return f"Initial extraction link from chunk {span_reference}."


def _evidence_snippet(
    evidence_payload: dict[str, object],
    *,
    claim: Claim,
) -> str | None:
    snippet = _first_normalized_item_string(evidence_payload, *_EVIDENCE_SNIPPET_KEYS)
    if snippet is not None:
        return snippet
    return _normalized_string(claim.exact_text)


def _evidence_score(evidence_payload: dict[str, object]) -> float | None:
    score = evidence_payload.get("score")
    if isinstance(score, int | float):
        return float(score)
    return None


def build_llm_claim_extractor(
    *,
    extract_claims: "ClaimExtractionGateway",
    normalize_claim: "ClaimNormalizationGateway | None" = None,
    claim_repository: "ClaimRepository | None" = None,
) -> _LlmClaimExtractor:
    """Bind the LLM claim extraction gateway into the application extraction shape."""

    return _LlmClaimExtractor(
        extract_claims=extract_claims,
        normalize_claim=normalize_claim,
        claim_repository=claim_repository,
    )


__all__ = ["build_llm_claim_extractor"]
